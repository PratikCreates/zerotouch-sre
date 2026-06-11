from __future__ import annotations

import pytest

from app.engine import ZeroTouchSREEngine, _extract_json_object
from app.billing_guard import BillingGuard
from app.mcp_client import DynatraceMCPClient


@pytest.mark.asyncio
async def test_engine_generates_post_mortem(tmp_path, monkeypatch):
    monkeypatch.setenv("ZEROTOUCH_DISABLE_LIVE", "1")
    engine = ZeroTouchSREEngine(
        mcp_client=DynatraceMCPClient(),
        billing_guard=BillingGuard(max_monthly_burn_limit_inr=900.0),
        reports_dir=tmp_path,
        write_root_samples=False,
    )

    result = await engine.handle_alert(
        {
            "incident_id": "INC-TEST-001",
            "service": "checkout-api",
            "severity": "critical",
            "title": "CPU spike and 500 errors",
        }
    )

    assert result.status == "mitigated"
    assert result.telemetry_mode == "mock"
    assert "CPU" in result.root_cause
    assert result.billing["total_tokens"] > 0
    report = tmp_path.joinpath(result.post_mortem_path.split("\\")[-1])
    runbook = tmp_path.joinpath(result.runbook_path.split("\\")[-1])
    trace = tmp_path.joinpath(result.trace_path.split("\\")[-1])
    audit = tmp_path / "mitigation_audit.jsonl"
    assert report.exists()
    assert runbook.exists()
    assert trace.exists()
    assert audit.exists()
    text = report.read_text(encoding="utf-8")
    assert "ZeroTouch SRE Post-Mortem" in text
    assert "Dynatrace MCP mode" in text
    assert "Incident Timeline" in text
    assert "Billing Guard Snapshot" in text
    runbook_text = runbook.read_text(encoding="utf-8")
    assert '"timeline"' in runbook_text
    assert '"audit_log"' in runbook_text
    trace_text = trace.read_text(encoding="utf-8")
    assert '"stages"' in trace_text
    assert '"google-adk"' in trace_text or '"deterministic-adk-compatible"' in trace_text


def test_billing_guard_blocks_excessive_burn():
    guard = BillingGuard(max_monthly_burn_limit_inr=0.001)

    with pytest.raises(Exception):
        guard.record(input_tokens=10_000, output_tokens=10_000)


@pytest.mark.asyncio
async def test_engine_uses_valid_live_gemini_json_for_reason_and_plan(tmp_path, monkeypatch):
    monkeypatch.setenv("ZEROTOUCH_DISABLE_LIVE", "1")
    engine = ZeroTouchSREEngine(
        mcp_client=DynatraceMCPClient(),
        billing_guard=BillingGuard(max_monthly_burn_limit_inr=900.0),
        reports_dir=tmp_path,
        write_root_samples=False,
    )

    def fake_live_json(*, phase: str, prompt: str, max_output_tokens: int):
        if phase == "reason":
            return {
                "_live_model": "gemini-test-live",
                "root_cause": "checkout-api exhausted workers after retry amplification pushed CPU and 500s above safe thresholds.",
                "confidence": 0.87,
                "evidence_count": 3,
            }
        if phase == "plan":
            return {
                "_live_model": "gemini-test-live",
                "strategy": "stabilize capacity, rollback the risky release, and coordinate owners",
                "risk": "low",
                "steps": [
                    {"action": "scale_service", "target": "checkout-api", "replicas": 9, "reason": "create immediate CPU headroom"},
                    {"action": "rollback_release", "target": "checkout-api", "version": "checkout-api:2026.06.07-rc2", "reason": "release correlates with the error spike"},
                    {"action": "open_incident_channel", "target": "INC-LIVE-JSON", "reason": "coordinate SRE and application owners"},
                ],
            }
        return None

    monkeypatch.setattr(engine, "_try_live_gemini_json", fake_live_json)

    result = await engine.handle_alert(
        {
            "incident_id": "INC-LIVE-JSON",
            "service": "checkout-api",
            "severity": "critical",
            "title": "Checkout CPU and 500 surge",
        }
    )

    assert result.root_cause.startswith("checkout-api exhausted workers")
    assert result.mitigation["actions"][0]["reason"] == "create immediate CPU headroom"
    trace = tmp_path.joinpath(result.trace_path.split("\\")[-1]).read_text(encoding="utf-8")
    assert '"source": "live-gemini-json"' in trace
    assert '"live_model_used": true' in trace


def test_extract_json_object_handles_fenced_model_output():
    parsed = _extract_json_object(
        """```json
{"root_cause": "cpu spike", "confidence": 0.8}
```"""
    )

    assert parsed == {"root_cause": "cpu spike", "confidence": 0.8}
