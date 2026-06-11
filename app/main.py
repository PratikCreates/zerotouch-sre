from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.billing_guard import BudgetGuardError
from app.engine import ZeroTouchSREEngine


ROOT = Path(__file__).resolve().parents[1]

app = FastAPI(
    title="ZeroTouch SRE",
    description="Autonomous SRE alert triage and mitigation backend for production operations teams.",
    version="0.1.0",
    docs_url=None,
    summary="Alert in, diagnosis and safe mitigation artifacts out.",
    contact={
        "name": "Pratik Shah",
        "url": "https://www.linkedin.com/in/pratikcreates",
    },
    license_info={
        "name": "MIT",
        "url": "https://github.com/PratikCreates/zerotouch-sre/blob/main/LICENSE",
    },
    openapi_tags=[
        {
            "name": "Product",
            "description": "Browser-facing routes for understanding, operating, and testing ZeroTouch SRE.",
        },
        {
            "name": "Incident Agent",
            "description": "Machine-to-machine endpoints that run the ZeroTouch SRE incident loop.",
        },
        {
            "name": "Operations",
            "description": "Readiness and service metadata for deployment checks.",
        },
    ],
)

app.mount("/assets", StaticFiles(directory=ROOT / "assets"), name="assets")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(ROOT / "assets" / "zerotouch_sre_logo.png", media_type="image/png")


class AlertPayload(BaseModel):
    incident_id: str = Field(
        default="INC-LOCAL-001",
        description="Stable incident identifier from an alerting system.",
        examples=["INC-CHECKOUT-20260607"],
    )
    service: str = Field(
        default="checkout-api",
        description="Affected service, workload, or business capability.",
        examples=["checkout-api"],
    )
    severity: str = Field(
        default="critical",
        description="Operational severity used by the agent when framing urgency.",
        examples=["critical"],
    )
    title: str = Field(
        default="Checkout API CPU spike",
        description="Human-readable alert title.",
        examples=["Checkout API CPU spike and HTTP 500 surge"],
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured alert context such as region, SLO, trigger, deploy id, or owner.",
        examples=[
            {
                "region": "us-central1",
                "slo": "checkout-availability",
                "trigger": "HTTP 500 rate above 5 percent for 10 minutes",
            }
        ],
    )
    # Judge-mode: optional per-request Dynatrace credential overrides.
    # Passed via the browser Connect panel; never logged or persisted server-side.
    # NOTE: exclude=True is intentionally NOT set — we need these in model_dump()
    # so engine.handle_alert() can pick them up to override Dynatrace credentials.
    dt_url: str | None = Field(
        default=None,
        description="Optional Dynatrace environment URL override (judge mode).",
        json_schema_extra={"x-hidden": True},
    )
    dt_token: str | None = Field(
        default=None,
        description="Optional Dynatrace API token override (judge mode).",
        json_schema_extra={"x-hidden": True},
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "incident_id": "INC-CHECKOUT-20260607",
                    "service": "checkout-api",
                    "severity": "critical",
                    "title": "Checkout API CPU spike and HTTP 500 surge",
                    "details": {
                        "region": "us-central1",
                        "slo": "checkout-availability",
                        "trigger": "HTTP 500 rate above 5 percent for 10 minutes",
                    },
                },
                {
                    "incident_id": "INC-WORLD-CUP-PAYMENTS",
                    "service": "ticketing-payments",
                    "severity": "high",
                    "title": "Payment failures during ticket sale surge",
                    "details": {
                        "region": "northamerica-northeast1",
                        "slo": "successful-payment-rate",
                        "trigger": "Payment authorization failures above 4 percent",
                        "business_event": "high-demand public ticket window",
                    },
                },
            ]
        }
    }


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    service: str = Field(examples=["zerotouch-sre"])


class TelemetrySummary(BaseModel):
    mode: str = Field(description="Telemetry mode used by the agent.", examples=["mock"])
    source: str = Field(description="Evidence source used in the incident loop.", examples=["mock-dynatrace"])
    live_attempted: bool = Field(description="Whether a live partner telemetry path was attempted.")
    fallback_note: str | None = Field(
        default=None,
        description="Sanitized fallback note when live telemetry is unavailable. No credentials are returned.",
        examples=["Dynatrace API fallback: HTTP Error 400: Bad Request"],
    )
    environment_url: str = Field(
        default="",
        description="Dynatrace environment URL used for this run (empty when mock).",
        examples=["https://wbu53242.live.dynatrace.com"],
    )


class BillingSnapshot(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_inr: float
    monthly_guardrail_inr: float
    credit_budget_inr: float


class ArtifactPreviews(BaseModel):
    post_mortem: str = Field(description="Safe text preview of the generated post-mortem artifact.")
    runbook: str = Field(description="Safe text preview of the generated runbook artifact.")


class AlertResponse(BaseModel):
    ok: bool
    incident_id: str
    status: str
    root_cause: str
    mitigation: dict[str, Any]
    telemetry_mode: str
    telemetry: TelemetrySummary
    post_mortem_path: str
    runbook_path: str
    trace_path: str
    artifact_previews: ArtifactPreviews
    billing: BillingSnapshot

    model_config = {
        "json_schema_extra": {
            "example": {
                "ok": True,
                "incident_id": "INC-CHECKOUT-20260607",
                "status": "mitigated",
                "root_cause": "checkout-api saturated CPU at 94.7% after payment retry loop changed from capped to unbounded; HTTP 500 rate reached 7.8% with p95 latency 1840 ms.",
                "mitigation": {
                    "mode": "simulation",
                    "actions": [
                        {
                            "sequence": 1,
                            "action": "scale_service",
                            "target": "checkout-api",
                            "status": "simulated_success",
                            "destructive": False,
                        }
                    ],
                },
                "telemetry_mode": "mock",
                "telemetry": {
                    "mode": "mock",
                    "source": "mock-dynatrace",
                    "live_attempted": True,
                    "fallback_note": "Dynatrace API fallback: HTTP Error 400: Bad Request",
                },
                "post_mortem_path": "/app/reports/post_mortem_20260606_210420.md",
                "runbook_path": "/app/reports/runbook_20260606_210421.json",
                "trace_path": "/app/reports/agent_trace_20260606_210421.json",
                "artifact_previews": {
                    "post_mortem": "# ZeroTouch SRE Post-Mortem\n\n## Incident Summary\n...",
                    "runbook": "{\n  \"incident_id\": \"INC-CHECKOUT-20260607\"\n}",
                },
                "billing": {
                    "input_tokens": 4500,
                    "output_tokens": 2000,
                    "total_tokens": 6500,
                    "estimated_cost_inr": 2.05425,
                    "monthly_guardrail_inr": 900.0,
                    "credit_budget_inr": 25000.0,
                },
            }
        }
    }


CHECKOUT_SCENARIO_ALERT = {
    "incident_id": "INC-CHECKOUT-20260607",
    "service": "checkout-api",
    "severity": "critical",
    "title": "Checkout API CPU spike and HTTP 500 surge",
    "details": {
        "region": "us-central1",
        "slo": "checkout-availability",
        "trigger": "HTTP 500 rate above 5 percent for 10 minutes",
    },
}


class _DynatraceTestPayload(BaseModel):
    dt_url: str
    dt_token: str


@app.post(
    "/dynatrace/test",
    include_in_schema=False,
    summary="Test a Dynatrace connection (judge mode)",
)
async def dynatrace_test(payload: _DynatraceTestPayload) -> dict[str, Any]:
    """Validate a judge-supplied Dynatrace token.

    Uses /api/v2/settings/schemas (requires any app-settings:objects:read scope)
    as a lightweight connectivity probe — this endpoint works on both SaaS and
    Platform editions and correctly 401s on bad tokens.
    Never persists credentials server-side.
    """
    import asyncio as _asyncio
    from urllib.request import Request as _Req, urlopen as _open
    from urllib.error import HTTPError as _HTTPError

    base = payload.dt_url.strip().rstrip("/")
    token = payload.dt_token.strip()
    if not base.startswith("https://"):
        return {"ok": False, "error": "URL must start with https://"}
    if not token:
        return {"ok": False, "error": "Token is required"}

    def _check() -> dict[str, Any]:
        headers = {"Authorization": f"Api-Token {token}", "Accept": "application/json"}

        # Primary probe: settings schemas — works with read scopes on SaaS + Platform
        probe_req = _Req(f"{base}/api/v2/settings/schemas?pageSize=1", headers=headers)
        try:
            with _open(probe_req, timeout=8) as resp:
                __import__("json").loads(resp.read().decode())
        except _HTTPError as exc:
            if exc.code == 401:
                return {"ok": False, "error": "Invalid token (401 Unauthorized)"}
            if exc.code == 403:
                return {"ok": False, "error": f"Token missing required scopes (403 Forbidden)"}
            return {"ok": False, "error": f"Dynatrace returned HTTP {exc.code}"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:200]}

        # Secondary check: OpenPipeline events ingest (push empty list → 202)
        try:
            op_req = _Req(
                f"{base}/platform/ingest/v1/events",
                data=b"[]",
                headers={**headers, "Content-Type": "application/json"},
                method="POST",
            )
            with _open(op_req, timeout=6):
                has_openpipeline = True
        except Exception:
            has_openpipeline = False

        # Extract hostname for display
        try:
            from urllib.parse import urlparse as _p
            env_host = _p(base).hostname or base
        except Exception:
            env_host = base

        return {
            "ok": True,
            "environment": base,
            "environment_host": env_host,
            "has_openpipeline": has_openpipeline,
            "scopes": ["app-settings:objects:read"] + (["openpipeline:events:ingest"] if has_openpipeline else []),
        }

    return await _asyncio.to_thread(_check)


@app.get(
    "/docs",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def api_docs() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ZeroTouch SRE - API Docs</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
  <link rel="icon" href="/assets/zerotouch_sre_logo.png" />
  <style>
    body { margin: 0; background: #081014; color: #f4fbfb; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    .docs-hero { display: grid; grid-template-columns: 104px 1fr auto; gap: 20px; align-items: center; padding: 24px clamp(16px, 4vw, 44px); border-bottom: 1px solid #263f49; background: radial-gradient(circle at 12% 0%, rgba(131,231,255,.18), transparent 32%), linear-gradient(135deg, #0b151b, #101a21); }
    .docs-hero img { width: 104px; height: 72px; object-fit: cover; border-radius: 10px; border: 1px solid #31525f; }
    .docs-hero h1 { margin: 0 0 6px; font-size: clamp(28px, 5vw, 48px); letter-spacing: -.04em; }
    .docs-hero p { margin: 0; color: #bdd0d6; line-height: 1.5; max-width: 760px; }
    .docs-actions { display: flex; flex-wrap: wrap; gap: 10px; justify-content: flex-end; }
    .docs-actions a { text-decoration: none; color: #06120b; background: #b8ffd7; border: 1px solid #b8ffd7; border-radius: 8px; padding: 10px 12px; font-weight: 900; white-space: nowrap; }
    .docs-actions a.secondary { color: #f4fbfb; background: #17242c; border-color: #345969; }
    #swagger-ui { background: #f7fafb; min-height: 100vh; }
    .swagger-ui .topbar { display: none; }
    @media (max-width: 820px) {
      .docs-hero { grid-template-columns: 76px 1fr; }
      .docs-hero img { width: 76px; height: 56px; }
      .docs-actions { grid-column: 1 / -1; justify-content: flex-start; }
    }
  </style>
</head>
<body>
  <header class="docs-hero">
    <img src="/assets/zerotouch_sre_logo.png" alt="ZeroTouch SRE logo" />
    <div>
      <h1>ZeroTouch SRE API</h1>
      <p>Use the checkout scenario for a guided operational review, inspect the raw JSON when needed, or send a custom payload to <strong>POST /alert</strong>.</p>
    </div>
    <nav class="docs-actions">
      <a href="/">Open website</a>
      <a class="secondary" href="/scenario">Run checkout scenario</a>
      <a class="secondary" href="https://github.com/PratikCreates/zerotouch-sre">GitHub</a>
    </nav>
  </header>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.ui = SwaggerUIBundle({
      url: "/openapi.json",
      dom_id: "#swagger-ui",
      deepLinking: true,
      displayRequestDuration: true,
      defaultModelsExpandDepth: 1,
      defaultModelExpandDepth: 2,
      tryItOutEnabled: true
    });
  </script>
</body>
</html>"""


@app.get(
    "/",
    response_class=HTMLResponse,
    tags=["Product"],
    summary="Open the interactive incident workbench",
    description=(
        "Returns the hosted product website with an embedded incident workbench. "
        "Use this as the primary project URL."
    ),
)
async def landing() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ZeroTouch SRE — Operational Workbench</title>
  <link rel="icon" href="/assets/zerotouch_sre_logo.png" />
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b1318;
      --panel: #111e25;
      --panel-2: #162831;
      --ink: #f5fcfc;
      --muted: #a3b8bf;
      --line: #2e4753;
      --mint: #34d399; /* Vibrant Mint */
      --cyan: #38bdf8; /* Vibrant Cyan */
      --amber: #fbbf24;
      --red: #f87171;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at 10% 5%, rgba(56, 189, 248, 0.08), transparent 25%),
        radial-gradient(circle at 90% 5%, rgba(52, 211, 153, 0.06), transparent 20%),
        #080f12;
      color: var(--ink);
    }
    main {
      width: min(1200px, calc(100vw - 24px));
      margin: 0 auto;
      padding: 16px 0 40px;
    }
    nav {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 18px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 12px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 900;
      letter-spacing: -.02em;
      font-size: 18px;
      text-decoration: none;
    }
    .mark {
      width: 42px;
      height: 30px;
      border: 1px solid var(--line);
      border-radius: 6px;
      object-fit: cover;
      background: #071016;
    }
    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(52, 211, 153, 0.1);
      border: 1px solid rgba(52, 211, 153, 0.25);
      color: var(--mint);
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.03em;
    }
    .status-dot {
      width: 6px;
      height: 6px;
      border-radius: 999px;
      background: var(--mint);
      animation: pulse 1.5s ease-in-out infinite;
    }
    .navlinks { display: flex; gap: 8px; flex-wrap: wrap; }
    .navlinks a, .button {
      text-decoration: none;
      border: 1px solid var(--line);
      background: rgba(17, 30, 37, 0.8);
      color: var(--ink);
      padding: 8px 12px;
      border-radius: 6px;
      font-weight: 700;
      font-size: 13px;
      transition: all 0.2s;
    }
    .navlinks a:hover, .button:hover {
      border-color: var(--cyan);
      background: rgba(22, 40, 49, 0.9);
    }
    .eyebrow {
      color: var(--cyan);
      font-weight: 900;
      letter-spacing: .12em;
      text-transform: uppercase;
      font-size: 10px;
    }
    .dashboard-intro {
      margin-bottom: 16px;
    }
    .dashboard-intro h1 {
      font-size: 26px;
      margin: 4px 0 6px;
      letter-spacing: -0.03em;
      font-weight: 900;
    }
    .dashboard-intro p {
      margin: 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }
    .workbench-dashboard {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr);
      gap: 16px;
      align-items: start;
    }
    .card {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 10px;
      padding: 16px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.18);
    }
    .card h2 {
      margin: 0 0 10px;
      font-size: 16px;
      font-weight: 800;
      letter-spacing: -.01em;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .card h2 span.subtitle {
      font-size: 11px;
      font-weight: 500;
      color: var(--muted);
    }
    .card p {
      margin: 0 0 12px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }
    textarea {
      width: 100%;
      min-height: 200px;
      resize: vertical;
      border: 1px solid var(--line);
      background: #070e12;
      color: #e6fff0;
      border-radius: 8px;
      padding: 12px;
      font: 12px/1.5 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      outline: none;
      transition: border-color 0.15s;
    }
    textarea:focus {
      border-color: var(--cyan);
      box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.1);
    }
    .buttonbar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }
    button {
      cursor: pointer;
      font: inherit;
    }
    .button.primary {
      background: var(--mint);
      color: #030a07;
      border-color: var(--mint);
      box-shadow: 0 4px 14px rgba(52, 211, 153, 0.15);
    }
    .button.primary:hover {
      background: #10b981;
      border-color: #10b981;
    }
    .statusline {
      color: var(--amber);
      font-weight: 800;
      margin-top: 8px;
      font-size: 12px;
      min-height: 18px;
    }
    /* Connect Panel Style */
    .dt-connect {
      border: 1px solid var(--line);
      background: linear-gradient(135deg, rgba(17, 30, 37, 0.8), rgba(22, 40, 49, 0.8));
      border-radius: 10px;
      padding: 14px 16px;
      margin-bottom: 12px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    }
    .dt-connect-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 10px;
    }
    .dt-connect-header h2 {
      margin: 0;
      font-size: 14px;
      font-weight: 800;
    }
    .dt-logo-mark {
      width: 20px;
      height: 20px;
      background: linear-gradient(135deg, var(--cyan), var(--mint));
      color: #080f12;
      border-radius: 4px;
      display: grid;
      place-items: center;
      font-size: 11px;
      font-weight: 900;
    }
    .dt-optional {
      font-size: 9px;
      font-weight: 900;
      letter-spacing: .05em;
      text-transform: uppercase;
      color: #64808c;
      border: 1px solid rgba(100, 128, 140, 0.3);
      border-radius: 999px;
      padding: 1px 6px;
      margin-left: auto;
    }
    .dt-fields {
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 8px;
    }
    .dt-field label {
      display: block;
      font-size: 10px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: .04em;
      color: #7aa0ae;
      margin-bottom: 4px;
    }
    .dt-field input {
      width: 100%;
      border: 1px solid var(--line);
      background: #070e12;
      color: #e6fff0;
      border-radius: 6px;
      padding: 8px 10px;
      font: 12px/1 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      outline: none;
    }
    .dt-field input:focus { border-color: var(--cyan); }
    .dt-actions {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-top: 10px;
      flex-wrap: wrap;
    }
    .dt-status {
      font-size: 12px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .dt-status.idle { color: #64808c; }
    .dt-status.checking { color: var(--amber); }
    .dt-status.ok { color: var(--mint); }
    .dt-status.err { color: #f87171; }
    .dt-status .dot { width: 6px; height: 6px; border-radius: 999px; background: currentColor; }
    .dt-hint {
      color: #5d7e8b;
      font-size: 11px;
      line-height: 1.4;
      margin-top: 8px;
    }
    .dt-scopes {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin-top: 6px;
    }
    .dt-scope-tag {
      font-size: 9px;
      font-weight: 800;
      background: #0d202d;
      border: 1px solid #1c3b57;
      color: var(--cyan);
      border-radius: 4px;
      padding: 1px 5px;
    }
    .dt-scope-tag.missing {
      color: #f87171;
      border-color: #501d1d;
      background: #1c0c0c;
    }
    /* Console Result Style */
    .console {
      border: 1px solid var(--line);
      background: #070e12;
      border-radius: 10px;
      overflow: hidden;
      box-shadow: 0 4px 24px rgba(0,0,0,0.22);
      min-height: 100%;
    }
    .console-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px;
      border-bottom: 1px solid var(--line);
      background: #111d24;
    }
    .lights { display: flex; gap: 5px; }
    .lights span { width: 8px; height: 8px; border-radius: 999px; display: block; }
    .lights .red { background: var(--red); }
    .lights .amber { background: var(--amber); }
    .lights .green { background: var(--mint); }
    .console-title { color: var(--muted); font-size: 12px; font-weight: 800; }
    .result-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      padding: 12px 14px;
    }
    .pill {
      border: 1px solid var(--line);
      background: rgba(17, 30, 37, 0.6);
      border-radius: 8px;
      padding: 10px;
    }
    .pill small {
      display: block;
      color: #7ba2af;
      text-transform: uppercase;
      letter-spacing: .06em;
      font-weight: 900;
      font-size: 9px;
      margin-bottom: 4px;
    }
    .pill strong {
      color: var(--mint);
      font-size: 13px;
      word-break: break-all;
    }
    .pill.large {
      grid-column: span 4;
    }
    .actions-list {
      margin: 8px 0 0;
      padding-left: 16px;
      color: #dceef2;
      font-size: 13px;
      line-height: 1.5;
    }
    .mini-artifacts {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 10px;
    }
    .mini-artifact {
      border: 1px solid var(--line);
      background: #081014;
      border-radius: 8px;
      overflow: hidden;
    }
    .mini-artifact h3 {
      margin: 0;
      padding: 8px 10px;
      border-bottom: 1px solid var(--line);
      color: var(--mint);
      font-size: 12px;
    }
    .mini-artifact pre {
      margin: 0;
      padding: 8px 10px;
      max-height: 160px;
      overflow: auto;
      color: #e2fceb;
      white-space: pre-wrap;
      font-size: 11px;
      line-height: 1.4;
    }
    .raw-output {
      max-height: 240px;
      border-top: 1px solid var(--line);
      margin: 10px 0 0;
      padding: 12px;
      background: #050b0e;
      overflow: auto;
      font-size: 11px;
      line-height: 1.45;
      color: #c9eede;
    }
    .hidden { display: none; }
    /* Horizontal flow at bottom */
    .flow-title {
      font-size: 15px;
      font-weight: 800;
      color: var(--cyan);
      margin: 24px 0 10px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .flow {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 10px;
      margin-bottom: 24px;
    }
    .step {
      border: 1px solid var(--line);
      background: rgba(16, 26, 33, 0.4);
      border-radius: 8px;
      padding: 12px;
      min-height: 100px;
    }
    .step strong {
      display: block;
      color: var(--mint);
      margin-bottom: 4px;
      font-size: 13px;
    }
    .step span {
      color: var(--muted);
      line-height: 1.35;
      font-size: 12px;
    }
    /* Info panels below fold */
    .section-head {
      margin-top: 30px;
      margin-bottom: 12px;
    }
    .section-head h2 {
      margin: 0 0 4px;
      font-size: 20px;
      letter-spacing: -.02em;
    }
    .section-head p {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
    }
    .innovation-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
    }
    .badge {
      display: inline-flex;
      background: rgba(56, 189, 248, 0.1);
      border: 1px solid rgba(56, 189, 248, 0.25);
      color: var(--cyan);
      border-radius: 4px;
      padding: 2px 6px;
      font-size: 9px;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 6px;
    }
    .innovation-grid .card h3 {
      margin: 0 0 6px;
      font-size: 14px;
      font-weight: 800;
    }
    .innovation-grid .card p {
      font-size: 12px;
      line-height: 1.4;
      margin: 0;
    }
    footer {
      color: #64808c;
      margin-top: 30px;
      font-size: 12px;
      text-align: center;
      border-top: 1px solid var(--line);
      padding-top: 14px;
    }
    @media (max-width: 900px) {
      .workbench-dashboard { grid-template-columns: 1fr; }
      .flow { grid-template-columns: 1fr; }
      .innovation-grid { grid-template-columns: 1fr; }
      .dt-fields { grid-template-columns: 1fr; }
      .result-grid { grid-template-columns: 1fr 1fr; }
      .pill.large { grid-column: span 2; }
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }
  </style>
</head>
<body>
  <main>
    <nav>
      <a class="brand" href="/">
        <img class="mark" src="/assets/zerotouch_sre_logo.png" alt="ZeroTouch SRE logo" />
        <span>ZeroTouch SRE</span>
        <div class="status-pill"><span class="status-dot"></span><span>Active System</span></div>
      </a>
      <div class="navlinks">
        <a href="/scenario">Scenario Review</a>
        <a href="/docs">Swagger Docs</a>
        <a href="/health">Health</a>
        <a href="https://github.com/PratikCreates/zerotouch-sre">GitHub</a>
      </div>
    </nav>

    <div class="dashboard-intro">
      <h1>Operational Incident Response Workbench</h1>
      <p>
        ZeroTouch SRE automates the first fifteen minutes of production outages. 
        It ingests webhooks, pulls log evidence from Dynatrace Grail, runs Vertex AI reasoning, checks policies, and drafts audit/post-mortem artifacts in under 5 seconds.
      </p>
    </div>

    <div class="workbench-dashboard">
      <!-- Left Column: Inputs -->
      <div>
        <!-- Dynatrace Connect Panel -->
        <div class="dt-connect" id="dtConnect" aria-label="Connect your Dynatrace environment">
          <div class="dt-connect-header">
            <div class="dt-logo-mark" aria-hidden="true">⬡</div>
            <h2>Connect Dynatrace Tenant</h2>
            <span class="dt-optional">Optional Connection</span>
          </div>
          <div class="dt-fields">
            <div class="dt-field">
              <label for="dtUrl">Environment URL</label>
              <input id="dtUrl" type="url" placeholder="https://xyz12345.live.dynatrace.com" autocomplete="off" spellcheck="false" />
            </div>
            <div class="dt-field">
              <label for="dtToken">API Ingest Token</label>
              <input id="dtToken" type="password" placeholder="dt0s16.xxxxxxxxxxxx…" autocomplete="off" spellcheck="false" />
            </div>
          </div>
          <div class="dt-actions">
            <button class="button secondary" id="dtTestBtn" type="button" style="padding: 6px 12px; font-size:12px;">Test connection</button>
            <div class="dt-status idle" id="dtStatus">
              <span class="dot"></span>
              <span id="dtStatusText" style="font-size:11px;">Disconnected</span>
            </div>
          </div>
          <div class="dt-scopes hidden" id="dtScopeList"></div>
          <div class="dt-hint">Enter your Dynatrace tenant to enable bidirectional OpenPipeline event ingestion and log search.</div>
        </div>

        <!-- Workbench Trigger Card -->
        <div class="card">
          <h2>
            <span>Alert Webhook Simulation</span>
            <span class="subtitle">POST /alert</span>
          </h2>
          <p>Edit the raw JSON payload below and trigger the autonomous triage loop.</p>
          <textarea id="payload" spellcheck="false">{
  "incident_id": "INC-CHECKOUT-20260607",
  "service": "checkout-api",
  "severity": "critical",
  "title": "Checkout API CPU spike and HTTP 500 surge",
  "details": {
    "region": "us-central1",
    "slo": "checkout-availability",
    "trigger": "HTTP 500 rate above 5 percent for 10 minutes"
  }
}</textarea>
          <div class="buttonbar">
            <button class="button primary" id="runDemo" type="button">Run checkout incident</button>
            <button class="button secondary" id="runCustom" type="button">Run edited alert</button>
            <button class="button secondary" id="resetPayload" type="button">Reset payload</button>
          </div>
          <div class="statusline" id="statusline">System ready. Select a scenario to run.</div>
        </div>
      </div>

      <!-- Right Column: Console Outputs -->
      <div class="console" aria-label="Incident result console">
        <div class="console-head">
          <div class="lights"><span class="green"></span><span class="amber"></span><span class="red"></span></div>
          <div class="console-title">TRIAGE ENGINE RESULTS</div>
        </div>
        <div class="result-grid" id="resultGrid">
          <div class="pill"><small>Triage Status</small><strong id="resultStatus">Waiting</strong></div>
          <div class="pill"><small>Telemetry Mode</small><strong id="resultTelemetry">Not Run</strong></div>
          <div class="pill"><small>Incident ID</small><strong id="resultIncident">-</strong></div>
          <div class="pill"><small>Gemini Cost</small><strong id="resultBudget">-</strong></div>
          <div class="pill large"><small>Root Cause Diagnosis</small><strong id="resultCause">Triage not executed yet. Click "Run checkout incident" to execute the loop.</strong></div>
        </div>
        <div style="padding: 0 14px 14px;">
          <small style="color: #7ba2af; text-transform: uppercase; font-size: 9px; font-weight: 950; display: block; margin-bottom: 6px;">Simulated Mitigation Actions</small>
          <ul class="actions-list" id="resultActions" style="margin: 0; padding-left: 18px;">
            <li style="color: var(--muted); list-style-type: square;">Triage loop plans allowlisted mitigations dynamically.</li>
          </ul>
          <div class="mini-artifacts hidden" id="artifactPreviews" aria-label="Generated artifact previews">
            <article class="mini-artifact">
              <h3>Post-mortem preview</h3>
              <pre id="postMortemPreview"></pre>
            </article>
            <article class="mini-artifact">
              <h3>Runbook preview</h3>
              <pre id="runbookPreview"></pre>
            </article>
          </div>
        </div>
        <pre class="raw-output hidden" id="rawOutput"></pre>
      </div>
    </div>

    <div class="flow-title">Autonomous Operational Loop</div>
    <section class="flow" aria-label="Agent workflow">
      <div class="step"><strong>1. Perceive</strong><span>Normalize incident webhook alert.</span></div>
      <div class="step"><strong>2. Retrieve</strong><span>Fetch live Grail logs via Dynatrace APIs.</span></div>
      <div class="step"><strong>3. Reason</strong><span>Analyze logs to determine root cause.</span></div>
      <div class="step"><strong>4. Plan</strong><span>Formulate allowlisted safety actions.</span></div>
      <div class="step"><strong>5. Execute</strong><span>Simulate playbooks and write artifacts.</span></div>
    </section>

    <div class="section-head">
      <h2>Operational capabilities</h2>
      <p>Built to be useful, safe, and cost-controlled for on-call engineers.</p>
    </div>

    <section class="innovation-grid" aria-label="Operational capabilities">
      <div class="card">
        <span class="badge">Action over chat</span>
        <h3>Webhook-to-artifact loop</h3>
        <p>A single webhook request produces a diagnosis, mitigation plans, post-mortem markdown, and JSON runbook.</p>
      </div>
      <div class="card">
        <span class="badge">Bidirectional Observability</span>
        <h3>Telemetry-first reasoning</h3>
        <p>Queries Grail logs dynamically and pushes audit events back into your Dynatrace tenant using OpenPipeline.</p>
      </div>
      <div class="card">
        <span class="badge">Safe autonomy</span>
        <h3>Allowlist policy gates</h3>
        <p>All production mitigations are simulation-only by default. Destructive actions require explicit operator approval.</p>
      </div>
    </section>

    <footer>
      ZeroTouch SRE • Deployed on Google Cloud Run • Source: <a href="https://github.com/PratikCreates/zerotouch-sre" style="color: var(--cyan);">github.com/PratikCreates/zerotouch-sre</a>
    </footer>
  </main>
  <script>
    const samplePayload = {
      incident_id: "INC-CHECKOUT-20260607",
      service: "checkout-api",
      severity: "critical",
      title: "Checkout API CPU spike and HTTP 500 surge",
      details: {
        region: "us-central1",
        slo: "checkout-availability",
        trigger: "HTTP 500 rate above 5 percent for 10 minutes"
      }
    };
    const payloadBox = document.getElementById("payload");
    const statusline = document.getElementById("statusline");
    const rawOutput = document.getElementById("rawOutput");
    const artifactPreviews = document.getElementById("artifactPreviews");
    const runDemoBtn = document.getElementById("runDemo");

    // ── Dynatrace Connect state ──
    let dtConnected = false;
    let dtEnv = { url: "", token: "" };

    function setStatus(text) { statusline.textContent = text; }
    function money(v) { return v == null ? "-" : "INR " + Number(v).toFixed(4); }

    // Update the Run button label based on DT connection state
    function syncRunButton() {
      runDemoBtn.textContent = dtConnected
        ? "Run with MY Dynatrace ⬡"
        : "Run checkout incident";
    }

    // ── DT connect panel ──
    const dtStatus    = document.getElementById("dtStatus");
    const dtStatusTxt = document.getElementById("dtStatusText");
    const dtScopeList = document.getElementById("dtScopeList");

    function setDtStatus(state, text) {
      dtStatus.className = "dt-status " + state;
      dtStatusTxt.textContent = text;
    }

    document.getElementById("dtTestBtn").addEventListener("click", async () => {
      const url   = document.getElementById("dtUrl").value.trim();
      const token = document.getElementById("dtToken").value.trim();
      if (!url || !token) { setDtStatus("err", "Enter both URL and token first"); return; }
      setDtStatus("checking", "Connecting…");
      dtScopeList.className = "dt-scopes hidden";
      try {
        const res  = await fetch("/dynatrace/test", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ dt_url: url, dt_token: token }),
        });
        const data = await res.json();
        if (data.ok) {
          dtConnected = true;
          dtEnv = { url, token };
          const env = data.environment_host || new URL(url).hostname;
          setDtStatus("ok", `Connected · ${env}`);
          
          // Save to localStorage
          localStorage.setItem("dt_url", url);
          localStorage.setItem("dt_token", token);

          // Show connection capability tags
          const tags = [
            `<span class="dt-scope-tag">✓ Authenticated</span>`,
            data.has_openpipeline
              ? `<span class="dt-scope-tag">✓ OpenPipeline ready</span>`
              : `<span class="dt-scope-tag missing">✗ openpipeline:events:ingest missing</span>`,
            `<span class="dt-scope-tag" style="margin-left:4px">Run below to push live events →</span>`,
          ];
          dtScopeList.innerHTML = tags.join("");
          dtScopeList.className = "dt-scopes";
        } else {
          dtConnected = false;
          setDtStatus("err", data.error || "Connection failed");
        }
      } catch (e) {
        dtConnected = false;
        setDtStatus("err", "Network error: " + e.message);
      }
      syncRunButton();
    });

    // Clear connection if URL/token edited
    ["dtUrl", "dtToken"].forEach(id => {
      document.getElementById(id).addEventListener("input", () => {
        if (dtConnected) {
          dtConnected = false;
          dtEnv = { url: "", token: "" };
          setDtStatus("idle", "Enter your environment URL and token");
          dtScopeList.className = "dt-scopes hidden";
          localStorage.removeItem("dt_url");
          localStorage.removeItem("dt_token");
          syncRunButton();
        }
      });
    });

    // Load from localStorage on startup
    window.addEventListener("DOMContentLoaded", () => {
      const savedUrl = localStorage.getItem("dt_url");
      const savedToken = localStorage.getItem("dt_token");
      if (savedUrl && savedToken) {
        document.getElementById("dtUrl").value = savedUrl;
        document.getElementById("dtToken").value = savedToken;
        document.getElementById("dtTestBtn").click();
      }
    });

    function renderResult(data) {
      const mode = (data.telemetry && data.telemetry.mode) || data.telemetry_mode || "-";
      const src  = (data.telemetry && data.telemetry.source) || "-";
      const envHtml = data.telemetry && data.telemetry.environment_url
        ? ` · <a href="${data.telemetry.environment_url}" target="_blank" style="color: var(--cyan); text-decoration: underline;">${new URL(data.telemetry.environment_url).hostname}</a>`
        : "";
      document.getElementById("resultStatus").textContent    = data.ok ? data.status : "failed";
      document.getElementById("resultTelemetry").innerHTML   = mode + " / " + src + envHtml;
      document.getElementById("resultIncident").textContent  = data.incident_id || "-";
      document.getElementById("resultBudget").textContent    = data.billing ? money(data.billing.estimated_cost_inr) : "-";
      document.getElementById("resultCause").textContent     = data.root_cause || "No root cause returned.";
      const actions = document.getElementById("resultActions");
      actions.innerHTML = "";
      const planned = data.mitigation && Array.isArray(data.mitigation.actions) ? data.mitigation.actions : [];
      planned.forEach(item => {
        const li = document.createElement("li");
        li.textContent = `${item.action} on ${item.target}: ${item.status}`;
        actions.appendChild(li);
      });
      const previews = data.artifact_previews || {};
      if (previews.post_mortem || previews.runbook) {
        artifactPreviews.classList.remove("hidden");
        document.getElementById("postMortemPreview").textContent = previews.post_mortem || "Post-mortem preview unavailable.";
        document.getElementById("runbookPreview").textContent    = previews.runbook || "Runbook preview unavailable.";
      } else {
        artifactPreviews.classList.add("hidden");
      }
      rawOutput.classList.remove("hidden");
      rawOutput.textContent = JSON.stringify(data, null, 2);
    }

    async function runPayload(payload) {
      // Inject judge-mode credentials if connected
      const body = dtConnected
        ? { ...payload, dt_url: dtEnv.url, dt_token: dtEnv.token }
        : payload;
      setStatus(dtConnected
        ? "Running with YOUR Dynatrace — pushing events and pulling logs…"
        : "Running incident loop…");
      rawOutput.classList.add("hidden");
      artifactPreviews.classList.add("hidden");
      const response = await fetch("/alert", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Request failed");
      renderResult(data);
      setStatus(dtConnected
        ? "Done. Events pushed to YOUR Dynatrace — check your environment."
        : "Completed. Review the diagnosis, actions, telemetry, and raw trace preview.");
    }

    runDemoBtn.addEventListener("click", async () => {
      payloadBox.value = JSON.stringify(samplePayload, null, 2);
      try { await runPayload(samplePayload); }
      catch (e) { setStatus("Error: " + e.message); }
    });

    document.getElementById("runCustom").addEventListener("click", async () => {
      try { await runPayload(JSON.parse(payloadBox.value)); }
      catch (e) { setStatus("Error: " + e.message); }
    });

    document.getElementById("resetPayload").addEventListener("click", () => {
      payloadBox.value = JSON.stringify(samplePayload, null, 2);
      setStatus("Payload reset.");
    });
  </script>
</body>
</html>"""


@app.get(
    "/health",
    tags=["Operations"],
    response_model=HealthResponse,
    summary="Check service readiness",
    description="Returns a small readiness payload for uptime monitors and quick deployment checks.",
)
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "zerotouch-sre"}


@app.get(
    "/scenario",
    tags=["Product", "Incident Agent"],
    response_class=HTMLResponse,
    summary="Open the checkout incident scenario",
    description=(
        "Runs the checkout outage scenario through the same engine used by POST /alert, "
        "then renders the result as a guided incident review page."
    ),
)
async def scenario() -> HTMLResponse:
    payload = await _run_checkout_scenario()
    return HTMLResponse(
        _render_scenario_result_page(payload),
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get(
    "/demo",
    tags=["Product", "Incident Agent"],
    response_class=HTMLResponse,
    include_in_schema=False,
    summary="Open the checkout incident scenario",
    description=(
        "Runs the checkout outage scenario through the same engine used by POST /alert, "
        "then renders the result as a guided incident review page."
    ),
)
async def demo() -> HTMLResponse:
    payload = await _run_checkout_scenario()
    return HTMLResponse(
        _render_scenario_result_page(payload),
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get(
    "/scenario.json",
    tags=["Incident Agent"],
    response_model=AlertResponse,
    summary="Run the checkout incident scenario as JSON",
    description=(
        "Runs the checkout outage scenario through the same engine used by POST /alert "
        "and returns the raw machine-readable response."
    ),
)
async def scenario_json() -> dict[str, Any]:
    return await _run_checkout_scenario()


@app.get(
    "/demo.json",
    tags=["Incident Agent"],
    response_model=AlertResponse,
    include_in_schema=False,
    summary="Run the checkout incident scenario as JSON",
    description=(
        "Runs the checkout outage scenario through the same engine used by POST /alert "
        "and returns the raw machine-readable response."
    ),
)
async def demo_json() -> dict[str, Any]:
    return await _run_checkout_scenario()


async def _run_checkout_scenario() -> dict[str, Any]:
    return await ingest_alert(AlertPayload(**CHECKOUT_SCENARIO_ALERT))


def _render_scenario_result_page(payload: dict[str, Any]) -> str:
    telemetry = payload.get("telemetry", {})
    billing = payload.get("billing", {})
    mitigation = payload.get("mitigation", {})
    actions = mitigation.get("actions", [])
    action_cards = "\n".join(
        f"""
        <article class="action-card">
          <span>{escape(str(item.get("sequence", "")))}</span>
          <div>
            <strong>{escape(_format_action_label(str(item.get("action", ""))))}</strong>
            <p>{escape(str(item.get("reason", "Safe simulated mitigation.")))}</p>
            <small>{escape(str(item.get("target", "")))} · {escape(str(item.get("status", "")))}</small>
          </div>
        </article>
        """
        for item in actions
    )
    raw_json = escape(__import__("json").dumps(payload, indent=2))
    root_cause = escape(str(payload.get("root_cause", "Root cause unavailable.")))
    incident_id = escape(str(payload.get("incident_id", "")))
    status = escape(str(payload.get("status", "")))
    raw_mode = str(telemetry.get("mode", payload.get("telemetry_mode", "")))
    raw_src = str(telemetry.get("source", ""))
    env_url = str(telemetry.get("environment_url", ""))
    if env_url:
        from urllib.parse import urlparse
        env_host = urlparse(env_url).hostname or env_url
        telemetry_display = f'{escape(raw_mode)} / {escape(raw_src)} · <a href="{escape(env_url)}" target="_blank" style="color: var(--cyan); text-decoration: underline;">{escape(env_host)}</a>'
    else:
        telemetry_display = f'{escape(raw_mode)} / {escape(raw_src)}'
    telemetry_source = escape(raw_src)
    fallback_note = escape(str(telemetry.get("fallback_note") or "Live telemetry succeeded or no fallback note was needed."))
    cost = escape(f"INR {float(billing.get('estimated_cost_inr', 0.0)):.4f}")
    tokens = escape(str(billing.get("total_tokens", "-")))
    artifact_list = [
        ("Post-mortem", payload.get("post_mortem_path", "")),
        ("Runbook", payload.get("runbook_path", "")),
        ("Agent trace", payload.get("trace_path", "")),
    ]
    artifacts = "\n".join(
        f"<li><strong>{escape(label)}</strong><span>{escape(str(path))}</span></li>"
        for label, path in artifact_list
    )
    post_mortem_preview = _artifact_preview(payload.get("post_mortem_path"), max_chars=2600)
    runbook_preview = _artifact_preview(payload.get("runbook_path"), max_chars=1800)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ZeroTouch SRE Incident Review</title>
  <link rel="icon" href="/assets/zerotouch_sre_logo.png" />
  <style>
    :root {{ color-scheme: dark; --bg:#081014; --panel:#101a21; --line:#2d4651; --ink:#f4fbfb; --muted:#b7c9cf; --mint:#b8ffd7; --cyan:#83e7ff; --amber:#ffd166; --red:#ff8f8f; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; background: radial-gradient(circle at 15% 0%, rgba(131,231,255,.16), transparent 30%), linear-gradient(135deg,#071016,#0f1715); color:var(--ink); }}
    main {{ width:min(1120px, calc(100vw - 34px)); margin:0 auto; padding:28px 0 48px; }}
    nav {{ display:flex; justify-content:space-between; align-items:center; gap:14px; margin-bottom:26px; }}
    .brand {{ display:flex; align-items:center; gap:12px; font-weight:900; }}
    .brand img {{ width:54px; height:38px; object-fit:cover; border:1px solid var(--line); border-radius:8px; }}
    .links {{ display:flex; flex-wrap:wrap; gap:10px; justify-content:flex-end; }}
    a {{ color:inherit; }}
    .button {{ text-decoration:none; border:1px solid var(--line); background:#17242c; padding:10px 13px; border-radius:8px; font-weight:850; }}
    .button.primary {{ background:var(--mint); color:#06120b; border-color:var(--mint); }}
    .review-note {{ display:flex; gap:10px; align-items:center; border:1px solid #31525f; background:#0c1a20; border-radius:10px; padding:12px 14px; margin-bottom:18px; color:var(--muted); }}
    .review-note strong {{ color:var(--mint); }}
    .pill {{ display:inline-flex; align-items:center; gap:8px; border:1px solid #31525f; background:#09151a; color:var(--cyan); border-radius:999px; padding:7px 10px; font-size:12px; font-weight:900; text-transform:uppercase; letter-spacing:.08em; }}
    .hero {{ display:grid; grid-template-columns: .9fr 1.1fr; gap:22px; align-items:stretch; }}
    .logo {{ width:100%; border:1px solid #31525f; border-radius:14px; box-shadow:0 24px 80px rgba(0,0,0,.28); }}
    .panel {{ border:1px solid var(--line); background:rgba(16,26,33,.82); border-radius:12px; padding:22px; }}
    .eyebrow {{ color:var(--cyan); text-transform:uppercase; letter-spacing:.13em; font-size:12px; font-weight:900; }}
    h1 {{ font-size:clamp(38px, 7vw, 72px); line-height:.93; margin:12px 0 16px; letter-spacing:-.05em; }}
    h2 {{ margin:0 0 12px; letter-spacing:-.03em; font-size:clamp(24px, 4vw, 38px); }}
    p {{ color:var(--muted); line-height:1.58; }}
    .status {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:20px 0; }}
    .metric {{ border:1px solid #31525f; background:#0b151b; border-radius:10px; padding:14px; }}
    .metric small {{ display:block; color:#8fb0ba; text-transform:uppercase; letter-spacing:.09em; font-weight:900; font-size:10px; margin-bottom:6px; }}
    .metric strong {{ color:var(--mint); word-break:break-word; }}
    .diagnosis {{ font-size:20px; color:#f7fffb; line-height:1.55; margin:0; }}
    .split {{ display:grid; grid-template-columns:1.05fr .95fr; gap:16px; margin-top:16px; }}
    .before-after {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:14px; }}
    .before-after div {{ border:1px solid #31525f; background:#0b151b; border-radius:10px; padding:14px; }}
    .before-after small {{ display:block; color:#8fb0ba; text-transform:uppercase; letter-spacing:.09em; font-size:10px; font-weight:900; margin-bottom:8px; }}
    .before-after strong {{ color:#f4fbfb; line-height:1.45; }}
    .before-after .bad strong {{ color:var(--red); }}
    .before-after .good strong {{ color:var(--mint); }}
    .flow {{ display:grid; grid-template-columns:repeat(5,1fr); gap:10px; margin-top:20px; }}
    .step {{ border:1px solid #31525f; border-radius:10px; padding:14px; background:#10212a; min-height:112px; }}
    .step strong {{ display:block; color:var(--mint); margin-bottom:7px; }}
    .step span {{ color:var(--muted); line-height:1.45; font-size:14px; }}
    .two {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:16px; }}
    .action-card {{ display:grid; grid-template-columns:40px 1fr; gap:12px; border:1px solid #31525f; border-radius:10px; padding:14px; background:#0b151b; margin-bottom:10px; }}
    .action-card > span {{ width:34px; height:34px; border-radius:999px; display:grid; place-items:center; background:var(--mint); color:#06120b; font-weight:900; }}
    .action-card strong {{ color:#f4fbfb; }}
    .action-card p {{ margin:5px 0; }}
    .action-card small {{ color:var(--cyan); }}
    ul.artifacts {{ list-style:none; margin:0; padding:0; display:grid; gap:10px; }}
    ul.artifacts li {{ border:1px solid #31525f; border-radius:10px; padding:13px; background:#0b151b; }}
    ul.artifacts strong {{ display:block; color:var(--mint); margin-bottom:4px; }}
    ul.artifacts span {{ color:var(--muted); word-break:break-all; }}
    .artifact-preview {{ display:grid; grid-template-columns:1.1fr .9fr; gap:14px; margin-top:16px; }}
    .artifact-card {{ border:1px solid #31525f; background:#0b151b; border-radius:10px; overflow:hidden; }}
    .artifact-card h3 {{ margin:0; padding:13px 15px; color:var(--mint); border-bottom:1px solid #263f49; }}
    .artifact-card pre {{ border-top:0; max-height:360px; white-space:pre-wrap; }}
    details {{ margin-top:16px; border:1px solid #31525f; border-radius:10px; background:#071016; overflow:hidden; }}
    summary {{ cursor:pointer; padding:14px 16px; color:var(--amber); font-weight:900; }}
    pre {{ margin:0; padding:16px; overflow:auto; color:#dff9e9; border-top:1px solid #263f49; font-size:13px; line-height:1.55; }}
    
    /* ── Dynatrace Connect Panel ── */
    .dt-connect {{ border: 1px solid #2a4a5a; background: linear-gradient(135deg,#0c1a22,#0f1e28); border-radius: 14px; padding: 22px 24px; margin: 20px 0; }}
    .dt-connect-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }}
    .dt-connect-header h2 {{ margin: 0; font-size: 20px; letter-spacing: -.02em; }}
    .dt-logo-mark {{ width: 28px; height: 28px; background: linear-gradient(135deg,#83e7ff,#b8ffd7); border-radius: 6px; display: grid; place-items: center; font-size: 14px; flex-shrink: 0; }}
    .dt-optional {{ font-size: 11px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: #5a8090; border: 1px solid #2a4a5a; border-radius: 999px; padding: 3px 8px; margin-left: auto; }}
    .dt-fields {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .dt-field label {{ display: block; font-size: 11px; font-weight: 900; text-transform: uppercase; letter-spacing: .09em; color: #7aa0ae; margin-bottom: 6px; }}
    .dt-field input {{ width: 100%; border: 1px solid #2d4651; background: #071016; color: #e6fff0; border-radius: 8px; padding: 10px 12px; font: 13px/1 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; outline: none; transition: border-color .15s; }}
    .dt-field input:focus {{ border-color: var(--cyan); box-shadow: 0 0 0 3px rgba(131,231,255,.1); }}
    .dt-field input::placeholder {{ color: #3a5562; }}
    .dt-actions {{ display: flex; align-items: center; gap: 12px; margin-top: 14px; flex-wrap: wrap; }}
    .dt-status {{ font-size: 13px; font-weight: 700; display: flex; align-items: center; gap: 7px; min-height: 20px; }}
    .dt-status.idle {{ color: #5a8090; }}
    .dt-status.checking {{ color: var(--amber); }}
    .dt-status.ok {{ color: var(--mint); }}
    .dt-status.err {{ color: #ff8f8f; }}
    .dt-status .dot {{ width: 8px; height: 8px; border-radius: 999px; background: currentColor; flex-shrink: 0; }}
    .dt-status.checking .dot {{ animation: pulse 1s ease-in-out infinite; }}
    @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:.3}} }}
    .dt-hint {{ color: #4a7080; font-size: 12px; line-height: 1.5; margin-top: 10px; }}
    .dt-hint code {{ font-size: 11px; }}
    .dt-scopes {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; }}
    .dt-scope-tag {{ font-size: 10px; font-weight: 800; background: #0e2230; border: 1px solid #1e4060; color: var(--cyan); border-radius: 4px; padding: 2px 7px; letter-spacing: .04em; }}
    .dt-scope-tag.missing {{ color: #ff8f8f; border-color: #4a2020; background: #1a0e0e; }}
    .hidden {{ display: none !important; }}

    @media (max-width: 900px) {{ .hero,.two,.split,.artifact-preview {{ grid-template-columns:1fr; }} .status,.flow {{ grid-template-columns:1fr 1fr; }} .dt-fields {{ grid-template-columns: 1fr; }} }}
    @media (max-width: 700px) {{ .before-after {{ grid-template-columns:1fr; }} }}
    @media (max-width: 560px) {{ main {{ width:min(100vw - 24px,1120px); }} nav {{ align-items:flex-start; flex-direction:column; }} .status,.flow {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <main>
    <nav>
      <div class="brand"><img src="/assets/zerotouch_sre_logo.png" alt="ZeroTouch SRE logo" /><span>ZeroTouch SRE</span></div>
      <div class="links">
        <a class="button primary" href="/">Open workbench</a>
        <a class="button" href="/scenario.json">Raw JSON</a>
        <a class="button" href="/docs">API docs</a>
        <a class="button" href="https://github.com/PratikCreates/zerotouch-sre">GitHub</a>
      </div>
    </nav>

    <div class="review-note">
      <span class="pill">Incident review</span>
      <span><strong>Checkout outage scenario:</strong> this page runs the alert through ZeroTouch SRE and summarizes the result for operators. The raw machine-readable response is separate at <a href="/scenario.json">/scenario.json</a>.</span>
    </div>

    <section class="hero">
      <img class="logo" src="/assets/zerotouch_sre_logo.png" alt="ZeroTouch SRE autonomous incident response" />
      <div class="panel">
        <div class="eyebrow">Incident run completed</div>
        <h1>Checkout incident stabilized.</h1>
        <p>A single alert comes in. ZeroTouch SRE checks operational context, builds a root-cause hypothesis, chooses policy-safe actions, and leaves a review trail for the human owner.</p>
        <div class="status">
          <div class="metric"><small>Status</small><strong id="resultStatus">{status}</strong></div>
          <div class="metric"><small>Incident</small><strong id="resultIncident">{incident_id}</strong></div>
          <div class="metric"><small>Telemetry</small><strong id="resultTelemetry">{telemetry_display}</strong></div>
          <div class="metric"><small>Estimated cost</small><strong id="resultBudget">{cost}</strong></div>
        </div>
      </div>
    </section>

    <!-- ── Dynatrace Connect Panel ── -->
    <div class="dt-connect" id="dtConnect" aria-label="Connect your Dynatrace environment">
      <div class="dt-connect-header">
        <div class="dt-logo-mark" aria-hidden="true">⬡</div>
        <h2>Connect your Dynatrace</h2>
        <span class="dt-optional">Optional</span>
      </div>
      <div class="dt-fields">
        <div class="dt-field">
          <label for="dtUrl">Environment URL</label>
          <input id="dtUrl" type="url" placeholder="https://xyz12345.live.dynatrace.com" autocomplete="off" spellcheck="false" />
        </div>
        <div class="dt-field">
          <label for="dtToken">API Token</label>
          <input id="dtToken" type="password" placeholder="dt0s16.xxxxxxxxxxxx…" autocomplete="off" spellcheck="false" />
        </div>
      </div>
      <div class="dt-actions">
        <button class="button secondary" id="dtTestBtn" type="button">Test connection</button>
        <button class="button primary hidden" id="dtRunScenarioBtn" type="button">Run scenario with your Dynatrace ⬡</button>
        <div class="dt-status idle" id="dtStatus">
          <span class="dot"></span>
          <span id="dtStatusText">Enter your environment URL and token</span>
        </div>
      </div>
      <div class="dt-hint">Needs <code>openpipeline:events:ingest</code> scope. When connected, ZeroTouch SRE pushes events to <em>your</em> Dynatrace and queries your logs — proving live bidirectional integration.</div>
      <div class="dt-scopes hidden" id="dtScopeList"></div>
    </div>

    <section class="panel" style="margin-top:16px;">
      <h2>Operational diagnosis</h2>
      <p class="diagnosis" id="resultCause">{root_cause}</p>
      <div class="before-after">
        <div class="bad"><small>Before</small><strong>Checkout was failing under CPU pressure, with rising HTTP 500s and slow payment retries.</strong></div>
        <div class="good"><small>After</small><strong>Capacity relief, rollback, and incident coordination were selected under a safe simulation policy.</strong></div>
      </div>
    </section>

    <section class="flow" aria-label="What the agent did">
      <div class="step"><strong>Detected</strong><span>Received a critical checkout alert.</span></div>
      <div class="step"><strong>Checked evidence</strong><span>Attempted partner telemetry and recorded source state.</span></div>
      <div class="step"><strong>Found cause</strong><span>Connected CPU, latency, errors, and release timing.</span></div>
      <div class="step"><strong>Chose actions</strong><span>Picked only safe simulated mitigations.</span></div>
      <div class="step"><strong>Documented</strong><span>Generated review artifacts and an agent trace.</span></div>
    </section>

    <section class="split">
      <div class="panel">
        <h2>Safe actions taken</h2>
        <div id="actionCardsContainer">
          {action_cards}
        </div>
      </div>
      <div class="panel">
        <h2>Evidence and controls</h2>
        <div class="metric"><small>Telemetry source</small><strong id="telemetrySource">{telemetry_source}</strong></div>
        <p id="fallbackNote">{fallback_note}</p>
        <div class="metric"><small>Total model tokens</small><strong id="totalTokens">{tokens}</strong></div>
        <p>Actions are simulated and policy-gated. No destructive production write is performed in this hosted environment.</p>
      </div>
    </section>

    <section class="panel" style="margin-top:16px;">
      <h2>How to review the incident</h2>
      <div class="flow" style="margin-top:0;">
        <div class="step"><strong>1. Confirm impact</strong><span>Check the incident status, affected service, and cost snapshot.</span></div>
        <div class="step"><strong>2. Read diagnosis</strong><span>Review how the symptoms map to the likely operational cause.</span></div>
        <div class="step"><strong>3. Inspect actions</strong><span>Verify that every mitigation has a policy-safe reason.</span></div>
        <div class="step"><strong>4. Open workbench</strong><span>Adjust the alert payload and rerun the workflow from the browser.</span></div>
        <div class="step"><strong>5. Keep artifacts</strong><span>Use the post-mortem, runbook, and trace paths for follow-up.</span></div>
      </div>
    </section>

    <section class="panel" style="margin-top:16px;">
      <h2>Generated artifacts</h2>
      <ul class="artifacts" id="artifactsList">{artifacts}</ul>
      <div class="artifact-preview" aria-label="Generated artifact previews">
        <article class="artifact-card">
          <h3>Post-mortem preview</h3>
          <pre id="postMortemPreview">{post_mortem_preview}</pre>
        </article>
        <article class="artifact-card">
          <h3>Runbook preview</h3>
          <pre id="runbookPreview">{runbook_preview}</pre>
        </article>
      </div>
      <details>
        <summary>Show raw API response</summary>
        <pre id="rawJson">{raw_json}</pre>
      </details>
    </section>
  </main>
  
  <script>
    const samplePayload = {{
      incident_id: "INC-CHECKOUT-20260607",
      service: "checkout-api",
      severity: "critical",
      title: "Checkout API CPU spike and HTTP 500 surge",
      details: {{
        region: "us-central1",
        slo: "checkout-availability",
        trigger: "HTTP 500 rate above 5 percent for 10 minutes"
      }}
    }};

    let dtConnected = false;
    let dtEnv = {{ url: "", token: "" }};

    function money(v) {{ return v == null ? "-" : "INR " + Number(v).toFixed(4); }}

    const dtStatus    = document.getElementById("dtStatus");
    const dtStatusTxt = document.getElementById("dtStatusText");
    const dtScopeList = document.getElementById("dtScopeList");
    const runBtn      = document.getElementById("dtRunScenarioBtn");

    function setDtStatus(state, text) {{
      dtStatus.className = "dt-status " + state;
      dtStatusTxt.textContent = text;
    }}

    function formatActionLabel(action) {{
      const labels = {{
        "scale_service": "Scale service capacity",
        "rollback_release": "Rollback risky release",
        "open_incident_channel": "Open incident channel",
      }};
      return labels[action] || action.replace(/_/g, " ").replace(/\\b\\w/g, c => c.toUpperCase());
    }}

    function renderResult(data) {{
      const mode = (data.telemetry && data.telemetry.mode) || data.telemetry_mode || "-";
      const src  = (data.telemetry && data.telemetry.source) || "-";
      const envHtml = data.telemetry && data.telemetry.environment_url
        ? ` · <a href="${{data.telemetry.environment_url}}" target="_blank" style="color: var(--cyan); text-decoration: underline;">${{new URL(data.telemetry.environment_url).hostname}}</a>`
        : "";
      document.getElementById("resultStatus").textContent    = data.ok ? data.status : "failed";
      document.getElementById("resultTelemetry").innerHTML   = mode + " / " + src + envHtml;
      document.getElementById("resultIncident").textContent  = data.incident_id || "-";
      document.getElementById("resultBudget").textContent    = data.billing ? money(data.billing.estimated_cost_inr) : "-";
      document.getElementById("resultCause").textContent     = data.root_cause || "No root cause returned.";
      
      // Update action cards
      const container = document.getElementById("actionCardsContainer");
      container.innerHTML = "";
      const planned = data.mitigation && Array.isArray(data.mitigation.actions) ? data.mitigation.actions : [];
      planned.forEach(item => {{
        const card = document.createElement("article");
        card.className = "action-card";
        card.innerHTML = `
          <span>${{item.sequence || ""}}</span>
          <div>
            <strong>${{formatActionLabel(item.action || "")}}</strong>
            <p>${{item.reason || "Safe simulated mitigation."}}</p>
            <small>${{item.target || ""}} · ${{item.status || ""}}</small>
          </div>
        `;
        container.appendChild(card);
      }});

      // Update evidence and controls
      document.getElementById("telemetrySource").textContent = src;
      document.getElementById("fallbackNote").textContent = (data.telemetry && data.telemetry.fallback_note) || "Live telemetry succeeded or no fallback note was needed.";
      document.getElementById("totalTokens").textContent = data.billing ? data.billing.total_tokens : "-";

      // Update artifacts list
      const artList = document.getElementById("artifactsList");
      artList.innerHTML = `
        <li><strong>Post-mortem</strong><span>${{data.post_mortem_path || ""}}</span></li>
        <li><strong>Runbook</strong><span>${{data.runbook_path || ""}}</span></li>
        <li><strong>Agent trace</strong><span>${{data.trace_path || ""}}</span></li>
      `;

      // Update previews
      const previews = data.artifact_previews || {{}};
      document.getElementById("postMortemPreview").textContent = previews.post_mortem || "Post-mortem preview unavailable.";
      document.getElementById("runbookPreview").textContent    = previews.runbook || "Runbook preview unavailable.";

      // Update raw JSON
      document.getElementById("rawJson").textContent = JSON.stringify(data, null, 2);
    }}

    document.getElementById("dtTestBtn").addEventListener("click", async () => {{
      const url   = document.getElementById("dtUrl").value.trim();
      const token = document.getElementById("dtToken").value.trim();
      if (!url || !token) {{ setDtStatus("err", "Enter both URL and token first"); return; }}
      setDtStatus("checking", "Connecting…");
      dtScopeList.className = "dt-scopes hidden";
      runBtn.classList.add("hidden");
      try {{
        const res  = await fetch("/dynatrace/test", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ dt_url: url, dt_token: token }}),
        }});
        const data = await res.json();
        if (data.ok) {{
          dtConnected = true;
          dtEnv = {{ url, token }};
          const env = data.environment_host || new URL(url).hostname;
          setDtStatus("ok", `Connected · ${{env}}`);
          
          localStorage.setItem("dt_url", url);
          localStorage.setItem("dt_token", token);

          const tags = [
            `<span class="dt-scope-tag">✓ Authenticated</span>`,
            data.has_openpipeline
              ? `<span class="dt-scope-tag">✓ OpenPipeline ready</span>`
              : `<span class="dt-scope-tag missing">✗ openpipeline:events:ingest missing</span>`,
          ];
          dtScopeList.innerHTML = tags.join("");
          dtScopeList.className = "dt-scopes";
          runBtn.classList.remove("hidden");
        }} else {{
          dtConnected = false;
          setDtStatus("err", data.error || "Connection failed");
        }}
      }} catch (e) {{
        dtConnected = false;
        setDtStatus("err", "Network error: " + e.message);
      }}
    }});

    // Clear connection if URL/token edited
    ["dtUrl", "dtToken"].forEach(id => {{
      document.getElementById(id).addEventListener("input", () => {{
        if (dtConnected) {{
          dtConnected = false;
          dtEnv = {{ url: "", token: "" }};
          setDtStatus("idle", "Enter your environment URL and token");
          dtScopeList.className = "dt-scopes hidden";
          runBtn.classList.add("hidden");
          localStorage.removeItem("dt_url");
          localStorage.removeItem("dt_token");
        }}
      }});
    }});

    runBtn.addEventListener("click", async () => {{
      if (!dtConnected) return;
      setDtStatus("checking", "Running scenario with YOUR Dynatrace...");
      try {{
        const body = {{ ...samplePayload, dt_url: dtEnv.url, dt_token: dtEnv.token }};
        const response = await fetch("/alert", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(body),
        }});
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Request failed");
        renderResult(data);
        const env = dtEnv.url ? new URL(dtEnv.url).hostname : "";
        setDtStatus("ok", `Success! Events pushed to Dynatrace · ${{env}}`);
      }} catch (e) {{
        setDtStatus("err", "Execution failed: " + e.message);
      }}
    }});

    // Load from localStorage on startup
    window.addEventListener("DOMContentLoaded", () => {{
      const savedUrl = localStorage.getItem("dt_url");
      const savedToken = localStorage.getItem("dt_token");
      if (savedUrl && savedToken) {{
        document.getElementById("dtUrl").value = savedUrl;
        document.getElementById("dtToken").value = savedToken;
        document.getElementById("dtTestBtn").click();
      }}
    }});
  </script>
</body>
</html>"""


def _artifact_preview(path_value: Any, *, max_chars: int) -> str:
    return escape(_artifact_text_preview(path_value, max_chars=max_chars))


def _artifact_text_preview(path_value: Any, *, max_chars: int) -> str:
    if not path_value:
        return "Artifact was not generated for this run."
    try:
        path = Path(str(path_value))
    except TypeError:
        return "Artifact path could not be read."
    if not path.exists() or not path.is_file():
        return "Artifact was generated in the running service environment."
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "Artifact preview is unavailable."
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "\n\n[preview truncated]"
    return text


def _format_action_label(action: str) -> str:
    labels = {
        "scale_service": "Scale service capacity",
        "rollback_release": "Rollback risky release",
        "open_incident_channel": "Open incident channel",
    }
    return labels.get(action, action.replace("_", " ").title())


@app.post(
    "/alert",
    tags=["Incident Agent"],
    response_model=AlertResponse,
    summary="Run the ZeroTouch SRE incident loop",
    description=(
        "Accepts an alert, attempts partner telemetry, reasons about root cause, "
        "creates a safe mitigation plan, simulates allowlisted actions, and returns "
        "paths for generated incident artifacts."
    ),
)
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
        "telemetry": {
            "mode": result.telemetry_mode,
            "source": result.telemetry_source,
            "live_attempted": result.telemetry_mode != "mock" or result.telemetry_error != "live integrations disabled",
            "fallback_note": result.telemetry_error,
            "environment_url": result.telemetry_environment_url,
        },
        "post_mortem_path": result.post_mortem_path,
        "runbook_path": result.runbook_path,
        "trace_path": result.trace_path,
        "artifact_previews": {
            "post_mortem": _artifact_text_preview(result.post_mortem_path, max_chars=1800),
            "runbook": _artifact_text_preview(result.runbook_path, max_chars=2600),
        },
        "billing": result.billing,
    }


def create_app() -> FastAPI:
    return app
