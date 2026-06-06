from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_ACTIONS = {
    "scale_service",
    "rollback_release",
    "open_incident_channel",
}


class MitigationPolicyError(ValueError):
    """Raised when a proposed mitigation violates the safe autonomy policy."""


@dataclass
class ActionExecutor:
    audit_path: Path

    def execute(self, plan: dict[str, Any]) -> dict[str, Any]:
        executed_at = datetime.now(timezone.utc).isoformat()
        actions = []
        policy = self._policy_snapshot()
        for index, step in enumerate(plan.get("steps", []), start=1):
            action = str(step.get("action", ""))
            if action not in ALLOWED_ACTIONS:
                raise MitigationPolicyError(f"Action '{action}' is not allowed by the simulation policy.")
            target = str(step.get("target", ""))
            if not target:
                raise MitigationPolicyError(f"Action '{action}' is missing a target.")
            actions.append(
                {
                    "sequence": index,
                    "action": action,
                    "target": target,
                    "status": "simulated_success",
                    "reason": str(step.get("reason", "policy-approved mitigation")),
                    "approval": "auto-approved by safe simulation allowlist",
                    "destructive": False,
                }
            )
        mitigation = {
            "mode": "simulation",
            "executed_at": executed_at,
            "policy": policy,
            "actions": actions,
            "customer_impact": "error rate and latency expected to recover after rollback propagation",
        }
        self._append_audit_entry(mitigation)
        return mitigation

    def _policy_snapshot(self) -> dict[str, Any]:
        return {
            "name": "safe-simulation-allowlist",
            "allowed_actions": sorted(ALLOWED_ACTIONS),
            "live_write_access": False,
            "requires_human_for_destructive_actions": True,
        }

    def _append_audit_entry(self, mitigation: dict[str, Any]) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(mitigation, sort_keys=True) + "\n")
