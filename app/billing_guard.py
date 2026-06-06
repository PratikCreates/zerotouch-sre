from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Any, Awaitable, Callable, TypeVar

from dotenv import load_dotenv


F = TypeVar("F", bound=Callable)

FLASH_INPUT_USD_PER_MILLION = 1.50
FLASH_OUTPUT_USD_PER_MILLION = 9.00
DEFAULT_USD_TO_INR = 83.0
DEFAULT_MAX_BURN_INR = 900.0


class BudgetGuardError(RuntimeError):
    """Raised when the simulated run would exceed the configured burn guard."""


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class BillingGuard:
    total_credit_budget_inr: float = 0.0
    max_monthly_burn_limit_inr: float = DEFAULT_MAX_BURN_INR
    usd_to_inr: float = DEFAULT_USD_TO_INR
    usage: TokenUsage = field(default_factory=TokenUsage)

    @classmethod
    def from_env(cls, env_path: str | Path | None = None) -> "BillingGuard":
        if env_path:
            load_dotenv(env_path, override=False)
        else:
            load_dotenv(override=False)
        total_budget = _float_env("GCP_TOTAL_CREDIT_BUDGET_INR", 0.0)
        burn_limit = _float_env("GCP_MAX_MONTHLY_BURN_LIMIT_INR", DEFAULT_MAX_BURN_INR)
        conversion = _float_env("USD_TO_INR", DEFAULT_USD_TO_INR)
        return cls(
            total_credit_budget_inr=total_budget,
            max_monthly_burn_limit_inr=burn_limit,
            usd_to_inr=conversion,
        )

    def estimate_cost_inr(self, input_tokens: int, output_tokens: int) -> float:
        input_usd = (input_tokens / 1_000_000) * FLASH_INPUT_USD_PER_MILLION
        output_usd = (output_tokens / 1_000_000) * FLASH_OUTPUT_USD_PER_MILLION
        return round((input_usd + output_usd) * self.usd_to_inr, 6)

    def current_cost_inr(self) -> float:
        return self.estimate_cost_inr(self.usage.input_tokens, self.usage.output_tokens)

    def record(self, input_tokens: int, output_tokens: int) -> dict[str, float | int]:
        projected_input = self.usage.input_tokens + max(0, input_tokens)
        projected_output = self.usage.output_tokens + max(0, output_tokens)
        projected_cost = self.estimate_cost_inr(projected_input, projected_output)
        if projected_cost >= self.max_monthly_burn_limit_inr:
            raise BudgetGuardError(
                f"Projected burn INR {projected_cost} approaches guardrail "
                f"{self.max_monthly_burn_limit_inr}."
            )
        self.usage.input_tokens = projected_input
        self.usage.output_tokens = projected_output
        return self.snapshot()

    def snapshot(self) -> dict[str, float | int]:
        return {
            "input_tokens": self.usage.input_tokens,
            "output_tokens": self.usage.output_tokens,
            "total_tokens": self.usage.total_tokens,
            "estimated_cost_inr": self.current_cost_inr(),
            "monthly_guardrail_inr": self.max_monthly_burn_limit_inr,
            "credit_budget_inr": self.total_credit_budget_inr,
        }


def guarded_llm_call(input_tokens: int, output_tokens: int) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            guard = _find_guard(args, kwargs)
            guard.record(input_tokens=input_tokens, output_tokens=output_tokens)
            return await func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def _find_guard(args: tuple, kwargs: dict[str, Any]) -> BillingGuard:
    if "billing_guard" in kwargs and isinstance(kwargs["billing_guard"], BillingGuard):
        return kwargs["billing_guard"]
    for item in args:
        guard = getattr(item, "billing_guard", None)
        if isinstance(guard, BillingGuard):
            return guard
        if isinstance(item, BillingGuard):
            return item
    return BillingGuard.from_env()


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default
