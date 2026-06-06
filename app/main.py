from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.billing_guard import BudgetGuardError
from app.engine import ZeroTouchSREEngine


app = FastAPI(
    title="ZeroTouch SRE",
    description="Autonomous SRE alert triage and mitigation backend for production operations teams.",
    version="0.1.0",
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
            "name": "Showcase",
            "description": "Browser-facing routes for quickly understanding and trying the hosted project.",
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


class AlertPayload(BaseModel):
    incident_id: str = Field(
        default="INC-LOCAL-001",
        description="Stable incident identifier from an alerting system.",
        examples=["INC-DEMO-20260607"],
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

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "incident_id": "INC-DEMO-20260607",
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


class BillingSnapshot(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_inr: float
    monthly_guardrail_inr: float
    credit_budget_inr: float


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
    billing: BillingSnapshot

    model_config = {
        "json_schema_extra": {
            "example": {
                "ok": True,
                "incident_id": "INC-DEMO-20260607",
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


DEMO_ALERT = {
    "incident_id": "INC-DEMO-20260607",
    "service": "checkout-api",
    "severity": "critical",
    "title": "Checkout API CPU spike and HTTP 500 surge",
    "details": {
        "region": "us-central1",
        "slo": "checkout-availability",
        "trigger": "HTTP 500 rate above 5 percent for 10 minutes",
    },
}


@app.get(
    "/",
    response_class=HTMLResponse,
    tags=["Showcase"],
    summary="Open the interactive hosted showcase",
    description=(
        "Returns the judge-facing project website with an embedded incident workbench. "
        "Use this as the primary hosted project URL."
    ),
)
async def landing() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ZeroTouch SRE</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #091116;
      --panel: #101a21;
      --panel-2: #14242c;
      --ink: #f4fbfb;
      --muted: #b7c9cf;
      --line: #2d4651;
      --mint: #b8ffd7;
      --cyan: #83e7ff;
      --amber: #ffd166;
      --red: #ff7b72;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at 18% 12%, rgba(131, 231, 255, .16), transparent 28%),
        radial-gradient(circle at 82% 8%, rgba(184, 255, 215, .12), transparent 24%),
        linear-gradient(135deg, #081014, #0b151b 42%, #0f1715);
      color: var(--ink);
    }
    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image: linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
      background-size: 42px 42px;
      mask-image: linear-gradient(to bottom, black, transparent 78%);
    }
    a { color: inherit; }
    main { width: min(1180px, calc(100vw - 36px)); margin: 0 auto; padding: 34px 0 52px; position: relative; }
    nav { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 54px; }
    .brand { display: flex; align-items: center; gap: 12px; font-weight: 900; letter-spacing: -.02em; }
    .mark { width: 34px; height: 34px; border: 1px solid var(--line); background: conic-gradient(from 180deg, var(--mint), var(--cyan), #1d2b34, var(--mint)); border-radius: 8px; box-shadow: 0 0 32px rgba(131,231,255,.18); }
    .navlinks { display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }
    .navlinks a, .button { text-decoration: none; border: 1px solid var(--line); background: rgba(16,26,33,.76); color: var(--ink); padding: 11px 14px; border-radius: 8px; font-weight: 800; font-size: 14px; }
    .navlinks a:hover, .button:hover { border-color: var(--cyan); }
    .hero { display: grid; grid-template-columns: minmax(0, 1.03fr) minmax(360px, .97fr); gap: 28px; align-items: stretch; }
    .eyebrow { color: var(--cyan); font-weight: 900; letter-spacing: .14em; text-transform: uppercase; font-size: 12px; }
    h1 { font-size: clamp(46px, 8vw, 92px); line-height: .9; margin: 14px 0 18px; letter-spacing: -0.055em; max-width: 760px; }
    .lede { color: #dce9ec; font-size: clamp(18px, 2vw, 22px); line-height: 1.55; max-width: 780px; margin: 0; }
    .actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 30px; }
    .button.primary { background: var(--mint); color: #06120b; border-color: var(--mint); box-shadow: 0 14px 42px rgba(184,255,215,.14); }
    .button.secondary { background: #17242c; }
    .summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 32px; max-width: 760px; }
    .metric { border: 1px solid var(--line); background: rgba(16,26,33,.72); border-radius: 10px; padding: 16px; min-height: 106px; }
    .metric b { display: block; font-size: 22px; margin-bottom: 8px; color: var(--mint); }
    .metric span { color: var(--muted); line-height: 1.45; font-size: 14px; }
    .console { border: 1px solid #335563; background: #081014; border-radius: 12px; overflow: hidden; box-shadow: 0 24px 80px rgba(0,0,0,.34); min-height: 100%; }
    .console-head { display: flex; align-items: center; justify-content: space-between; padding: 13px 16px; border-bottom: 1px solid #243943; background: #111d24; }
    .lights { display: flex; gap: 7px; }
    .lights span { width: 10px; height: 10px; border-radius: 999px; display: block; }
    .red { background: var(--red); } .amber { background: var(--amber); } .green { background: var(--mint); }
    .console-title { color: var(--muted); font-size: 13px; font-weight: 800; }
    pre { margin: 0; padding: 18px; overflow: auto; color: #dff9e9; font-size: 13px; line-height: 1.55; }
    .token { color: var(--cyan); }
    section { margin-top: 28px; }
    .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
    .innovation-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    .card { border: 1px solid var(--line); background: rgba(16,26,33,.78); border-radius: 10px; padding: 18px; }
    .card h2, .card h3 { margin: 0 0 10px; letter-spacing: -.02em; }
    .card p, .card li { color: var(--muted); line-height: 1.55; }
    .card p { margin: 0; }
    .flow { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
    .step { border: 1px solid #31525f; background: #10212a; border-radius: 10px; padding: 16px; min-height: 132px; position: relative; }
    .step strong { display: block; color: var(--mint); margin-bottom: 8px; }
    .step span { color: var(--muted); line-height: 1.45; font-size: 14px; }
    .try { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .workbench { display: grid; grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr); gap: 16px; align-items: stretch; }
    textarea {
      width: 100%;
      min-height: 252px;
      resize: vertical;
      border: 1px solid #31525f;
      background: #071016;
      color: #e6fff0;
      border-radius: 10px;
      padding: 14px;
      font: 13px/1.55 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      outline: none;
    }
    textarea:focus { border-color: var(--cyan); box-shadow: 0 0 0 3px rgba(131,231,255,.12); }
    .buttonbar { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }
    button { cursor: pointer; font: inherit; }
    .result-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 14px; }
    .pill { border: 1px solid #31525f; background: #0b151b; border-radius: 10px; padding: 12px; }
    .pill small { display: block; color: #8fb0ba; text-transform: uppercase; letter-spacing: .09em; font-weight: 900; font-size: 10px; margin-bottom: 6px; }
    .pill strong { color: var(--mint); font-size: 15px; word-break: break-word; }
    .statusline { color: var(--amber); font-weight: 900; margin: 12px 0 0; min-height: 22px; }
    .actions-list { margin: 12px 0 0; padding-left: 18px; color: #d9e8eb; line-height: 1.55; }
    .raw-output { max-height: 280px; border-top: 1px solid #243943; margin-top: 14px; }
    .hidden { display: none; }
    .section-head { display: flex; align-items: end; justify-content: space-between; gap: 16px; margin: 34px 0 14px; }
    .section-head h2 { margin: 0; font-size: clamp(28px, 4vw, 44px); letter-spacing: -.04em; }
    .section-head p { margin: 0; max-width: 560px; color: var(--muted); line-height: 1.55; }
    .badge { display: inline-flex; align-items: center; gap: 8px; width: fit-content; border: 1px solid #3a6070; background: #0b171e; border-radius: 999px; padding: 7px 10px; color: var(--cyan); font-size: 12px; font-weight: 900; letter-spacing: .07em; text-transform: uppercase; margin-bottom: 14px; }
    code { background: #071016; border: 1px solid #26323b; padding: 2px 6px; border-radius: 6px; color: #fff4ba; }
    footer { color: #8fa5ad; margin-top: 36px; font-size: 14px; }
    @media (max-width: 900px) {
      .hero, .try, .workbench { grid-template-columns: 1fr; }
      .grid, .flow, .innovation-grid { grid-template-columns: 1fr 1fr; }
      .summary { grid-template-columns: 1fr; }
      .section-head { display: block; }
    }
    @media (max-width: 560px) {
      main { width: min(100vw - 24px, 1180px); padding-top: 18px; }
      nav { align-items: flex-start; flex-direction: column; margin-bottom: 36px; }
      .grid, .flow, .innovation-grid { grid-template-columns: 1fr; }
      .navlinks { justify-content: flex-start; }
      h1 { font-size: 44px; }
    }
  </style>
</head>
<body>
  <main>
    <nav>
      <div class="brand"><div class="mark"></div><span>ZeroTouch SRE</span></div>
      <div class="navlinks">
        <a href="/demo">Run Demo</a>
        <a href="/docs">API Docs</a>
        <a href="/health">Health</a>
        <a href="https://github.com/PratikCreates/zerotouch-sre">GitHub</a>
      </div>
    </nav>

    <div class="hero">
      <div>
        <div class="eyebrow">Agentic incident operations</div>
        <h1>From alert to action plan in one request.</h1>
        <p class="lede">
          ZeroTouch SRE receives a production alert, gathers Dynatrace evidence when available,
          reasons through root cause, simulates approved mitigations, and returns a post-mortem,
          runbook, trace, and budget snapshot.
        </p>
        <div class="actions">
          <a class="button primary" href="/demo">Run sample incident</a>
          <a class="button secondary" href="/docs">Try custom alert</a>
          <a class="button secondary" href="https://github.com/PratikCreates/zerotouch-sre">Review source</a>
        </div>
        <div class="summary">
          <div class="metric"><b>1 request</b><span>Webhook in, operational artifacts out.</span></div>
          <div class="metric"><b>Safe by design</b><span>Only allowlisted actions are simulated.</span></div>
          <div class="metric"><b>Auditable</b><span>Every stage is written to an agent trace.</span></div>
        </div>
      </div>
      <div class="console" aria-label="Sample incident payload">
        <div class="console-head">
          <div class="lights"><span class="red"></span><span class="amber"></span><span class="green"></span></div>
          <div class="console-title">sample_alert.json</div>
        </div>
        <pre>{
  <span class="token">"incident_id"</span>: "INC-DEMO-20260607",
  <span class="token">"service"</span>: "checkout-api",
  <span class="token">"severity"</span>: "critical",
  <span class="token">"title"</span>: "Checkout API CPU spike and HTTP 500 surge",
  <span class="token">"details"</span>: {
    <span class="token">"region"</span>: "us-central1",
    <span class="token">"slo"</span>: "checkout-availability",
    <span class="token">"trigger"</span>: "HTTP 500 rate above 5 percent for 10 minutes"
  }
}</pre>
      </div>
    </div>

    <section class="flow" aria-label="Agent workflow">
      <div class="step"><strong>Perceive</strong><span>Normalize alert fields into an incident record.</span></div>
      <div class="step"><strong>Retrieve</strong><span>Attempt Dynatrace evidence, then fall back deterministically if needed.</span></div>
      <div class="step"><strong>Reason</strong><span>Identify likely root cause with confidence and evidence count.</span></div>
      <div class="step"><strong>Plan</strong><span>Build a mitigation sequence that can be checked against policy.</span></div>
      <div class="step"><strong>Execute</strong><span>Simulate approved actions and generate review artifacts.</span></div>
    </section>

    <section class="try">
      <div class="card">
        <h2>Fast judge path</h2>
        <p>Use the workbench below. It runs the included checkout incident through the full agent loop and renders the result directly on this page.</p>
      </div>
      <div class="card">
        <h2>Custom alert path</h2>
        <p>Edit the alert JSON, run it, and compare root cause, telemetry mode, safe actions, generated artifacts, and budget guardrails.</p>
      </div>
    </section>

    <section class="workbench" aria-label="Interactive incident workbench">
      <div class="card">
        <h2>Incident workbench</h2>
        <p>Run the sample alert or edit the payload before sending it to <code>POST /alert</code>.</p>
        <textarea id="payload" spellcheck="false">{
  "incident_id": "INC-DEMO-20260607",
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
          <button class="button primary" id="runDemo" type="button">Run sample incident</button>
          <button class="button secondary" id="runCustom" type="button">Run edited alert</button>
          <button class="button secondary" id="resetPayload" type="button">Reset payload</button>
        </div>
        <div class="statusline" id="statusline">Ready.</div>
      </div>
      <div class="console" aria-label="Agent result">
        <div class="console-head">
          <div class="lights"><span class="green"></span><span class="amber"></span><span class="red"></span></div>
          <div class="console-title">agent result</div>
        </div>
        <div class="result-grid" id="resultGrid" style="padding: 16px;">
          <div class="pill"><small>Status</small><strong id="resultStatus">Waiting</strong></div>
          <div class="pill"><small>Telemetry</small><strong id="resultTelemetry">Not run</strong></div>
          <div class="pill"><small>Incident</small><strong id="resultIncident">-</strong></div>
          <div class="pill"><small>Budget</small><strong id="resultBudget">-</strong></div>
        </div>
        <div style="padding: 0 16px 16px;">
          <div class="pill">
            <small>Root cause</small>
            <strong id="resultCause">Run the demo to generate a diagnosis.</strong>
          </div>
          <ul class="actions-list" id="resultActions"></ul>
        </div>
        <pre class="raw-output hidden" id="rawOutput"></pre>
      </div>
    </section>

    <div class="section-head">
      <h2>Key innovations</h2>
      <p>ZeroTouch SRE is designed as an operational agent, not a chatbot wrapper. The demo is built to show execution quality, safety, and real-world usefulness in the first minute.</p>
    </div>

    <section class="innovation-grid" aria-label="Key innovations">
      <div class="card">
        <span class="badge">Action over chat</span>
        <h3>Webhook-to-artifact loop</h3>
        <p>A single alert request produces a diagnosis, mitigation plan, safe execution record, post-mortem path, runbook path, and trace path.</p>
      </div>
      <div class="card">
        <span class="badge">Partner signal</span>
        <h3>Telemetry-first reasoning</h3>
        <p>The agent attempts Dynatrace evidence before planning. If live telemetry is unavailable, it records a sanitized fallback note and still completes the workflow.</p>
      </div>
      <div class="card">
        <span class="badge">Safe autonomy</span>
        <h3>Policy-gated mitigation</h3>
        <p>Only approved simulated actions can run. Destructive production writes are blocked by design, keeping operators in control.</p>
      </div>
      <div class="card">
        <span class="badge">Audit ready</span>
        <h3>Traceable decisions</h3>
        <p>Each phase is captured: perceive, retrieve telemetry, reason, plan, execute, and synthesize. This makes the agent reviewable after the incident.</p>
      </div>
      <div class="card">
        <span class="badge">Cost aware</span>
        <h3>Budget guardrails</h3>
        <p>Every simulated model step records token usage and estimated INR burn, with a hard guardrail for excessive loops.</p>
      </div>
      <div class="card">
        <span class="badge">Cloud native</span>
        <h3>Hosted for testing</h3>
        <p>The project is containerized and deployed on Cloud Run with secret-backed provider configuration and public testing routes.</p>
      </div>
    </section>

    <section class="grid" aria-label="Why it stands out">
      <div class="card"><h3>Google Cloud ready</h3><p>Containerized FastAPI service deployed on Cloud Run with secret-backed provider configuration.</p></div>
      <div class="card"><h3>Partner-aware</h3><p>Dynatrace evidence is attempted first; fallback mode is explicit and auditable in the response.</p></div>
      <div class="card"><h3>Operator control</h3><p>Production-affecting changes are not performed blindly. The service simulates and records policy-approved actions.</p></div>
      <div class="card"><h3>Useful artifacts</h3><p>Each run produces a post-mortem, runbook, mitigation audit trail, and trace for review.</p></div>
    </section>

    <footer>
      Hosted on Google Cloud Run. Source: <a href="https://github.com/PratikCreates/zerotouch-sre">github.com/PratikCreates/zerotouch-sre</a>
    </footer>
  </main>
  <script>
    const samplePayload = {
      incident_id: "INC-DEMO-20260607",
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

    function setStatus(text) {
      statusline.textContent = text;
    }

    function money(value) {
      if (value === undefined || value === null) return "-";
      return "INR " + Number(value).toFixed(4);
    }

    function renderResult(data) {
      document.getElementById("resultStatus").textContent = data.ok ? data.status : "failed";
      document.getElementById("resultTelemetry").textContent = (data.telemetry && data.telemetry.mode ? data.telemetry.mode : data.telemetry_mode || "-") + " / " + (data.telemetry && data.telemetry.source ? data.telemetry.source : "-");
      document.getElementById("resultIncident").textContent = data.incident_id || "-";
      document.getElementById("resultBudget").textContent = data.billing ? money(data.billing.estimated_cost_inr) : "-";
      document.getElementById("resultCause").textContent = data.root_cause || "No root cause returned.";
      const actions = document.getElementById("resultActions");
      actions.innerHTML = "";
      const planned = data.mitigation && Array.isArray(data.mitigation.actions) ? data.mitigation.actions : [];
      planned.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = `${item.action} on ${item.target}: ${item.status}`;
        actions.appendChild(li);
      });
      rawOutput.classList.remove("hidden");
      rawOutput.textContent = JSON.stringify(data, null, 2);
    }

    async function runPayload(payload) {
      setStatus("Running incident loop...");
      rawOutput.classList.add("hidden");
      const response = await fetch("/alert", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Request failed");
      }
      renderResult(data);
      setStatus("Completed. Review the diagnosis, actions, telemetry, and raw trace preview.");
    }

    document.getElementById("runDemo").addEventListener("click", async () => {
      payloadBox.value = JSON.stringify(samplePayload, null, 2);
      try {
        await runPayload(samplePayload);
      } catch (error) {
        setStatus("Error: " + error.message);
      }
    });

    document.getElementById("runCustom").addEventListener("click", async () => {
      try {
        await runPayload(JSON.parse(payloadBox.value));
      } catch (error) {
        setStatus("Error: " + error.message);
      }
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
    "/demo",
    tags=["Showcase", "Incident Agent"],
    response_model=AlertResponse,
    summary="Run the built-in checkout incident",
    description=(
        "Runs the sample checkout alert through the same engine used by POST /alert. "
        "This is the fastest JSON-only judging path."
    ),
)
async def demo() -> dict[str, Any]:
    return await ingest_alert(AlertPayload(**DEMO_ALERT))


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
        },
        "post_mortem_path": result.post_mortem_path,
        "runbook_path": result.runbook_path,
        "trace_path": result.trace_path,
        "billing": result.billing,
    }


def create_app() -> FastAPI:
    return app
