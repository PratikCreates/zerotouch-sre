from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.billing_guard import BillingGuard
from app.engine import ZeroTouchSREEngine
from app.main import app
from app.mcp_client import DynatraceMCPClient


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_alert_webhook_triggers_engine_and_report(monkeypatch, tmp_path):
    monkeypatch.setenv("ZEROTOUCH_DISABLE_LIVE", "1")
    monkeypatch.setattr(
        "app.main.ZeroTouchSREEngine",
        lambda: ZeroTouchSREEngine(
            mcp_client=DynatraceMCPClient(),
            billing_guard=BillingGuard(max_monthly_burn_limit_inr=900.0),
            reports_dir=tmp_path,
            write_root_samples=False,
        ),
    )
    client = TestClient(app)
    response = client.post(
        "/alert",
        json={
            "incident_id": "INC-WEBHOOK-001",
            "service": "checkout-api",
            "severity": "critical",
            "title": "Checkout API CPU spike and 500 errors",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["status"] == "mitigated"
    assert payload["telemetry_mode"] == "mock"
    assert payload["mitigation"]["mode"] == "simulation"
    report_path = Path(payload["post_mortem_path"])
    runbook_path = Path(payload["runbook_path"])
    trace_path = Path(payload["trace_path"])
    assert report_path.exists()
    assert runbook_path.exists()
    assert trace_path.exists()
