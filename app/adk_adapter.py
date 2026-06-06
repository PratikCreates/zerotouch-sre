from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any


@dataclass(frozen=True)
class ADKRuntimeStatus:
    available: bool
    mode: str
    detail: str
    fast_model: str
    synthesis_model: str


class GeminiADKAdapter:
    """Small compatibility layer around the Google ADK package.

    Runtime environments can expose different Google ADK surfaces. This adapter
    records whether the package is importable and exposes model-role metadata
    without binding the core incident loop to a single ADK release surface.
    """

    def __init__(self, fast_model: str, synthesis_model: str) -> None:
        self.fast_model = fast_model
        self.synthesis_model = synthesis_model
        self.status = self._detect_runtime()

    def describe(self) -> dict[str, Any]:
        return {
            "available": self.status.available,
            "mode": self.status.mode,
            "detail": self.status.detail,
            "model_roles": {
                "perceive_reason_plan": self.status.fast_model,
                "post_mortem_synthesis": self.status.synthesis_model,
            },
        }

    def step_metadata(self, phase: str) -> dict[str, Any]:
        model = self.synthesis_model if phase == "synthesis" else self.fast_model
        return {
            "phase": phase,
            "runtime": self.status.mode,
            "model": model,
            "adk_available": self.status.available,
        }

    def _detect_runtime(self) -> ADKRuntimeStatus:
        candidates = ("google.adk", "google.adk.agents")
        for module_name in candidates:
            try:
                import_module(module_name)
                return ADKRuntimeStatus(
                    available=True,
                    mode="google-adk",
                    detail=f"Imported {module_name}.",
                    fast_model=self.fast_model,
                    synthesis_model=self.synthesis_model,
                )
            except Exception as exc:
                last_error = str(exc)[:180]
        return ADKRuntimeStatus(
            available=False,
            mode="deterministic-adk-compatible",
            detail=f"google-adk package not importable in this runtime; deterministic agent loop active ({last_error}).",
            fast_model=self.fast_model,
            synthesis_model=self.synthesis_model,
        )
