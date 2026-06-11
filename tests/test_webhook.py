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
    assert "artifact_previews" in payload
    assert "ZeroTouch SRE Post-Mortem" in payload["artifact_previews"]["post_mortem"]
    assert '"id": "INC-WEBHOOK-001"' in payload["artifact_previews"]["runbook"]
    report_path = Path(payload["post_mortem_path"])
    runbook_path = Path(payload["runbook_path"])
    trace_path = Path(payload["trace_path"])
    assert report_path.exists()
    assert runbook_path.exists()
    assert trace_path.exists()


def test_checkout_scenario_routes_are_product_facing(monkeypatch, tmp_path):
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

    page = client.get("/scenario")
    assert page.status_code == 200
    assert "Checkout incident stabilized." in page.text
    assert "INC-CHECKOUT-20260607" in page.text
    assert "Post-mortem preview" in page.text
    assert "Runbook preview" in page.text
    assert "ZeroTouch SRE Post-Mortem" in page.text
    assert "&quot;mitigation&quot;" in page.text
    assert "INC-DEMO" not in page.text
    assert "Incident sandbox" not in page.text

    payload = client.get("/scenario.json")
    assert payload.status_code == 200
    data = payload.json()
    assert data["ok"] is True
    assert data["incident_id"] == "INC-CHECKOUT-20260607"
    assert "ZeroTouch SRE Post-Mortem" in data["artifact_previews"]["post_mortem"]
    assert '"mitigation"' in data["artifact_previews"]["runbook"]


def test_compatibility_demo_routes_are_hidden_from_openapi():
    client = TestClient(app)
    paths = client.get("/openapi.json").json()["paths"]

    assert "/scenario" in paths
    assert "/scenario.json" in paths
    assert "/demo" not in paths
    assert "/demo.json" not in paths
