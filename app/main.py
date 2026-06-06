from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.billing_guard import BudgetGuardError
from app.engine import ZeroTouchSREEngine


app = FastAPI(
    title="ZeroTouch SRE",
    description="Autonomous SRE alert triage and mitigation backend for production operations teams.",
    version="0.1.0",
)


class AlertPayload(BaseModel):
    incident_id: str = Field(default="INC-LOCAL-001")
    service: str = Field(default="checkout-api")
    severity: str = Field(default="critical")
    title: str = Field(default="Checkout API CPU spike")
    details: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "zerotouch-sre"}


@app.post("/alert")
async def ingest_alert(payload: AlertPayload) -> dict[str, Any]:
    engine = ZeroTouchSREEngine()
    try:
        result = await engine.handle_alert(payload.model_dump())
    except BudgetGuardError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    return {
        "ok": True,
        "incident_id": result.incident_id,
        "status": result.status,
        "root_cause": result.root_cause,
        "mitigation": result.mitigation,
        "telemetry_mode": result.telemetry_mode,
        "post_mortem_path": result.post_mortem_path,
        "runbook_path": result.runbook_path,
        "trace_path": result.trace_path,
        "billing": result.billing,
    }


def create_app() -> FastAPI:
    return app
