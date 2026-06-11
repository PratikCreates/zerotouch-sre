"""
ZeroTouch SRE — Dynatrace OpenPipeline Batch Ingester
Pushes rich, realistic incident scenario events into Dynatrace.
Endpoint: POST /platform/ingest/v1/events (confirmed 202 OK)
Scope: openpipeline:events:ingest
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from dotenv import load_dotenv

ROOT = r"C:\Users\prati\Downloads\Projects\ZeroTouch SRE"
load_dotenv(os.path.join(ROOT, ".env"))

base_url = os.getenv("DYNATRACE_URL", "").strip().rstrip("/")
api_key = os.getenv("DYNATRACE_API_KEY", "").strip()

if not base_url or not api_key:
    print("ERROR: DYNATRACE_URL or DYNATRACE_API_KEY not set in .env")
    sys.exit(1)

INGEST_URL = f"{base_url}/platform/ingest/v1/events"
now = datetime.now(timezone.utc)

def ts(offset_minutes: int = 0) -> str:
    return (now - timedelta(minutes=abs(offset_minutes))).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

def ingest(batch: list[dict], label: str) -> bool:
    req = Request(
        INGEST_URL,
        data=json.dumps(batch).encode("utf-8"),
        headers={
            "Authorization": f"Api-Token {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=10) as resp:
            print(f"  [{resp.status}] {label} — {len(batch)} events ingested OK")
            return True
    except HTTPError as exc:
        print(f"  [ERROR {exc.code}] {label}: {exc.read().decode()[:120]}")
        return False
    except Exception as exc:
        print(f"  [ERROR] {label}: {exc}")
        return False

print(f"Target: {INGEST_URL}")
print(f"Time base: {ts()}")
print()

# ─── SCENARIO 1: Checkout API outage (the core demo scenario) ─────────────────
print("SCENARIO 1: checkout-api CPU + HTTP 500 spike...")
checkout_events = [
    {
        "timestamp": ts(45),
        "event.name": "zerotouch.checkout.deploy",
        "service": "checkout-api",
        "content": "Deployment checkout-api:2026.06.07-rc2 rolled out to us-central1",
        "severity": "INFO",
        "incident_id": "INC-CHECKOUT-20260607",
        "zerotouch.sre": "true",
        "release_version": "2026.06.07-rc2",
        "region": "us-central1",
    },
    {
        "timestamp": ts(30),
        "event.name": "zerotouch.checkout.warn",
        "service": "checkout-api",
        "content": "checkout-api CPU utilization crossed 70% threshold",
        "severity": "WARN",
        "incident_id": "INC-CHECKOUT-20260607",
        "zerotouch.sre": "true",
        "metric.cpu_pct": "72.1",
    },
    {
        "timestamp": ts(25),
        "event.name": "zerotouch.checkout.warn",
        "service": "checkout-api",
        "content": "payment-service dependency health check failed (2/3 retries)",
        "severity": "WARN",
        "incident_id": "INC-CHECKOUT-20260607",
        "zerotouch.sre": "true",
        "dependency": "payment-service",
    },
    {
        "timestamp": ts(20),
        "event.name": "zerotouch.checkout.error",
        "service": "checkout-api",
        "content": "HTTP 500 rate exceeded 5% threshold — SLO breach imminent",
        "severity": "ERROR",
        "incident_id": "INC-CHECKOUT-20260607",
        "zerotouch.sre": "true",
        "metric.http_500_rate_pct": "5.8",
        "slo": "checkout-availability",
    },
    {
        "timestamp": ts(18),
        "event.name": "zerotouch.checkout.error",
        "service": "checkout-api",
        "content": "CPU utilization 88% — HPA at max replicas, scale-out blocked",
        "severity": "ERROR",
        "incident_id": "INC-CHECKOUT-20260607",
        "zerotouch.sre": "true",
        "metric.cpu_pct": "88.4",
        "metric.hpa_replicas": "10",
        "metric.hpa_max": "10",
    },
    {
        "timestamp": ts(15),
        "event.name": "zerotouch.sre.alert.received",
        "service": "checkout-api",
        "content": "ZeroTouch SRE received: Checkout API CPU spike and HTTP 500 surge",
        "severity": "CRITICAL",
        "incident_id": "INC-CHECKOUT-20260607",
        "zerotouch.sre": "true",
        "zerotouch.auto_remediation": "true",
        "zerotouch.agent": "ZeroTouchSREEngine/1.0",
    },
    {
        "timestamp": ts(14),
        "event.name": "zerotouch.sre.triage.started",
        "service": "checkout-api",
        "content": "AI triage initiated — fetching telemetry from Dynatrace OpenPipeline",
        "severity": "INFO",
        "incident_id": "INC-CHECKOUT-20260607",
        "zerotouch.sre": "true",
        "zerotouch.phase": "perceive",
    },
    {
        "timestamp": ts(13),
        "event.name": "zerotouch.sre.root_cause",
        "service": "checkout-api",
        "content": (
            "Root cause identified: checkout-api:2026.06.07-rc2 introduced "
            "blocking DB connection pooling. payment-service timeouts cascade → "
            "CPU spike → HPA ceiling → HTTP 500 surge."
        ),
        "severity": "INFO",
        "incident_id": "INC-CHECKOUT-20260607",
        "zerotouch.sre": "true",
        "zerotouch.phase": "reason",
        "zerotouch.root_cause": "regression-in-release",
        "zerotouch.confidence": "high",
    },
    {
        "timestamp": ts(12),
        "event.name": "zerotouch.sre.mitigation.planned",
        "service": "checkout-api",
        "content": "Safety-gated mitigation plan: [1] rollback_release [2] scale_service [3] open_incident_channel",
        "severity": "INFO",
        "incident_id": "INC-CHECKOUT-20260607",
        "zerotouch.sre": "true",
        "zerotouch.phase": "plan",
        "zerotouch.actions_planned": "3",
    },
    {
        "timestamp": ts(11),
        "event.name": "zerotouch.sre.mitigation.executed",
        "service": "checkout-api",
        "content": "Simulated rollback to checkout-api:2026.06.06-stable — awaiting human approval for production apply",
        "severity": "INFO",
        "incident_id": "INC-CHECKOUT-20260607",
        "zerotouch.sre": "true",
        "zerotouch.phase": "execute",
        "zerotouch.action": "rollback_release",
        "zerotouch.action_status": "simulated",
        "zerotouch.target_version": "2026.06.06-stable",
    },
    {
        "timestamp": ts(10),
        "event.name": "zerotouch.sre.artifacts.written",
        "service": "checkout-api",
        "content": "Artifacts written: post-mortem, runbook JSON, agent trace, mitigation audit log",
        "severity": "INFO",
        "incident_id": "INC-CHECKOUT-20260607",
        "zerotouch.sre": "true",
        "zerotouch.phase": "synthesize",
        "zerotouch.artifacts": "post_mortem,runbook,agent_trace,mitigation_audit",
    },
]
ingest(checkout_events, "Scenario 1: checkout-api outage")

# ─── SCENARIO 2: Payment service timeout cascade ───────────────────────────────
print("\nSCENARIO 2: payment-service timeout cascade...")
payment_events = [
    {
        "timestamp": ts(120),
        "event.name": "zerotouch.payment.warn",
        "service": "payment-service",
        "content": "Stripe gateway latency elevated — p95=850ms (baseline 200ms)",
        "severity": "WARN",
        "incident_id": "INC-PAYMENT-20260606",
        "zerotouch.sre": "true",
        "metric.p95_latency_ms": "850",
        "dependency": "stripe-gateway",
    },
    {
        "timestamp": ts(115),
        "event.name": "zerotouch.payment.error",
        "service": "payment-service",
        "content": "Payment authorization timeout after 3 retries — connection pool exhausted",
        "severity": "ERROR",
        "incident_id": "INC-PAYMENT-20260606",
        "zerotouch.sre": "true",
        "metric.connection_pool_wait_ms": "4200",
    },
    {
        "timestamp": ts(110),
        "event.name": "zerotouch.sre.alert.received",
        "service": "payment-service",
        "content": "ZeroTouch SRE received: Payment Service Timeout Cascade",
        "severity": "CRITICAL",
        "incident_id": "INC-PAYMENT-20260606",
        "zerotouch.sre": "true",
        "zerotouch.auto_remediation": "true",
    },
    {
        "timestamp": ts(108),
        "event.name": "zerotouch.sre.mitigation.executed",
        "service": "payment-service",
        "content": "Circuit breaker pattern applied — downstream traffic shed to fallback queue",
        "severity": "INFO",
        "incident_id": "INC-PAYMENT-20260606",
        "zerotouch.sre": "true",
        "zerotouch.action": "scale_service",
        "zerotouch.action_status": "simulated",
    },
]
ingest(payment_events, "Scenario 2: payment-service cascade")

# ─── SCENARIO 3: Auth service pod OOMKill ─────────────────────────────────────
print("\nSCENARIO 3: auth-service OOMKill...")
auth_events = [
    {
        "timestamp": ts(60),
        "event.name": "zerotouch.auth.error",
        "service": "auth-service",
        "content": "Pod auth-service-7f8d4 OOMKilled — memory limit 512Mi exceeded",
        "severity": "ERROR",
        "incident_id": "INC-AUTH-20260605",
        "zerotouch.sre": "true",
        "metric.memory_mb": "538",
        "metric.limit_mb": "512",
        "pod": "auth-service-7f8d4",
    },
    {
        "timestamp": ts(58),
        "event.name": "zerotouch.sre.alert.received",
        "service": "auth-service",
        "content": "ZeroTouch SRE: Auth Service OOMKill — login failures spiking",
        "severity": "CRITICAL",
        "incident_id": "INC-AUTH-20260605",
        "zerotouch.sre": "true",
        "zerotouch.auto_remediation": "true",
    },
    {
        "timestamp": ts(56),
        "event.name": "zerotouch.sre.root_cause",
        "service": "auth-service",
        "content": "Root cause: JWT validation cache unbounded growth after token refresh bug introduced in v1.4.2",
        "severity": "INFO",
        "incident_id": "INC-AUTH-20260605",
        "zerotouch.sre": "true",
        "zerotouch.root_cause": "memory-leak",
        "zerotouch.confidence": "high",
    },
]
ingest(auth_events, "Scenario 3: auth-service OOMKill")

print("\n=== All batches sent. Summary ===")
print(f"Total events: {len(checkout_events) + len(payment_events) + len(auth_events)}")
print(f"Dynatrace environment: {base_url}")
print(f"View in Dynatrace: {base_url}/ui/apps/dynatrace.davis.problems")
print("Search filter: 'zerotouch.sre = true'")
print("Done.")
