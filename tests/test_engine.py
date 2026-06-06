from __future__ import annotations

import pytest

from app.engine import ZeroTouchSREEngine
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
