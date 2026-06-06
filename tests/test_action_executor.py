from __future__ import annotations

import json

import pytest

from app.action_executor import ActionExecutor, MitigationPolicyError


def test_action_executor_allowlists_safe_simulated_actions(tmp_path):
    executor = ActionExecutor(audit_path=tmp_path / "audit.jsonl")
    result = executor.execute(
        {
            "steps": [
                {"action": "scale_service", "target": "checkout-api", "reason": "high cpu"},
                {"action": "rollback_release", "target": "checkout-api", "reason": "bad deploy"},
            ]
        }
    )

    assert result["mode"] == "simulation"
    assert result["policy"]["live_write_access"] is False
    assert len(result["actions"]) == 2
    assert result["actions"][0]["approval"] == "auto-approved by safe simulation allowlist"
    audit_lines = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(audit_lines) == 1
    assert json.loads(audit_lines[0])["actions"][1]["action"] == "rollback_release"


def test_action_executor_rejects_unapproved_actions(tmp_path):
    executor = ActionExecutor(audit_path=tmp_path / "audit.jsonl")

    with pytest.raises(MitigationPolicyError):
        executor.execute({"steps": [{"action": "delete_database", "target": "primary"}]})
