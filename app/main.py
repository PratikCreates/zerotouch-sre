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
)


class AlertPayload(BaseModel):
    incident_id: str = Field(default="INC-LOCAL-001")
    service: str = Field(default="checkout-api")
    severity: str = Field(default="critical")
    title: str = Field(default="Checkout API CPU spike")
    details: dict[str, Any] = Field(default_factory=dict)


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


@app.get("/", response_class=HTMLResponse)
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
    .card { border: 1px solid var(--line); background: rgba(16,26,33,.78); border-radius: 10px; padding: 18px; }
    .card h2, .card h3 { margin: 0 0 10px; letter-spacing: -.02em; }
    .card p, .card li { color: var(--muted); line-height: 1.55; }
    .card p { margin: 0; }
    .flow { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
    .step { border: 1px solid #31525f; background: #10212a; border-radius: 10px; padding: 16px; min-height: 132px; position: relative; }
    .step strong { display: block; color: var(--mint); margin-bottom: 8px; }
    .step span { color: var(--muted); line-height: 1.45; font-size: 14px; }
    .try { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    code { background: #071016; border: 1px solid #26323b; padding: 2px 6px; border-radius: 6px; color: #fff4ba; }
    footer { color: #8fa5ad; margin-top: 36px; font-size: 14px; }
    @media (max-width: 900px) {
      .hero, .try { grid-template-columns: 1fr; }
      .grid, .flow { grid-template-columns: 1fr 1fr; }
      .summary { grid-template-columns: 1fr; }
    }
    @media (max-width: 560px) {
      main { width: min(100vw - 24px, 1180px); padding-top: 18px; }
      nav { align-items: flex-start; flex-direction: column; margin-bottom: 36px; }
      .grid, .flow { grid-template-columns: 1fr; }
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
        <p>Open <code>/demo</code>. It runs the included checkout incident through the full agent loop and returns JSON with root cause, mitigation, telemetry metadata, artifact paths, and billing.</p>
      </div>
      <div class="card">
        <h2>Custom alert path</h2>
        <p>Open <code>/docs</code>, expand <code>POST /alert</code>, choose Try it out, paste the sample payload or your own service alert, then execute.</p>
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
</body>
</html>"""


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "zerotouch-sre"}


@app.get("/demo")
async def demo() -> dict[str, Any]:
    return await ingest_alert(AlertPayload(**DEMO_ALERT))


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
