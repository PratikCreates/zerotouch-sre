# ZeroTouch SRE

Autonomous incident triage, safe mitigation simulation, and post-mortem generation for the **Google Cloud Rapid Agent Hackathon: Building Agents for Real-World Challenges**.

ZeroTouch SRE is a machine-to-machine backend that turns a production alert into an evidence-backed SRE response. It receives an alert through FastAPI, attempts live Dynatrace telemetry, falls back safely when live access fails, uses Gemini-role orchestration to reason and plan, gates every mitigation through a safe action policy, and writes both a human post-mortem and a machine-readable incident runbook.

## The Problem

During incidents, SRE teams lose time switching between alert payloads, logs, dashboards, release notes, mitigation playbooks, and post-incident documentation. The first ten minutes are often the most expensive: the team needs enough evidence to act, but manual triage is slow and inconsistent.

ZeroTouch SRE targets that gap. It does not pretend to be an unbounded production operator. It is a controlled agent that can gather context, explain its reasoning, simulate approved mitigations, and preserve a complete evidence trail for humans.

## What It Does

1. Accepts a production alert at `POST /alert`.
2. Normalizes the alert into an incident record.
3. Attempts live Dynatrace telemetry using real `.env` credentials when available.
4. Falls back to deterministic Dynatrace-style telemetry if live auth, API, or MCP routing fails.
5. Uses the `gemini-3.5-flash` role for fast perceive, reason, and plan steps.
6. Runs proposed actions through a safe simulation allowlist.
7. Writes an append-only mitigation audit log.
8. Uses the `gemini-3.1-pro` role for post-mortem synthesis when live Gemini is available.
9. Generates:
   - `demo_response.json`
   - `post_mortem.md`
   - `runbook.json`
   - `agent_trace.json`
   - timestamped report artifacts in `reports/`

## Architecture

```text
Incoming alert
  |
  v
FastAPI /alert
  |
  v
Perceive
  - normalize incident id, service, severity, title
  |
  v
Telemetry lookup
  - live Dynatrace API when credentials work
  - optional Dynatrace MCP command route
  - deterministic mock fallback
  |
  v
Reason and plan
  - gemini-3.5-flash role
  - Google ADK adapter metadata
  - root cause, confidence, mitigation strategy
  |
  v
Safe action executor
  - allowlisted simulated actions only
  - rejects unapproved/destructive actions
  - writes reports/mitigation_audit.jsonl
  |
  v
Synthesis
  - gemini-3.1-pro role when available
  - deterministic markdown fallback
  |
  v
Post-mortem + runbook + API response
```

## Hackathon Fit

**Technological Implementation**

- FastAPI backend with a real webhook surface.
- Google/Gemini model roles implemented in the incident engine.
- Dynatrace partner telemetry path with live-first behavior.
- MCP-compatible command route plus direct API attempt.
- Deterministic fallback keeps demos reliable.
- Budget guard tracks simulated token cost against INR limits.
- Dockerfile for Cloud Run deployment.

**Design**

- No UI needed: this is an operational backend pipeline.
- Clear input/output contract: alert in, mitigation/report/runbook out.
- Human-safe autonomy: the agent cannot perform destructive live writes.
- Every action is auditable.

**Potential Impact**

- Reduces time from alert to initial diagnosis.
- Standardizes post-mortem quality.
- Makes AI-assisted SRE safer by separating recommendation/simulation from destructive execution.
- Provides a path for teams to adopt agentic operations incrementally.

**Quality of Idea**

Most incident assistants stop at chat. ZeroTouch SRE completes the operational loop: alert ingestion, telemetry evidence, reasoning, planning, policy-gated mitigation, audit logging, post-mortem generation, and machine-readable runbook output.

## Key Files

```text
app/
  main.py              FastAPI app with /health and /alert
  engine.py            Incident orchestration loop
  adk_adapter.py       Google ADK compatibility and model-role metadata
  mcp_client.py        Dynatrace MCP/direct API client with fallback
  mock_dynatrace.py    Deterministic telemetry for demos/tests
  action_executor.py   Safe mitigation executor and audit log writer
  billing_guard.py     Token/cost guardrail
scripts/
  capture_demo.py      One-command demo artifact capture
  cloud_run_preflight.py Secret-safe Cloud Run deploy readiness helper
  devpost_readiness.py Submission-readiness audit
tests/
  test_*.py            Engine, webhook, safety, deliverable checks
```

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
python scripts\capture_demo.py --live
python -m pytest -q
```

`--live` tries real Dynatrace and Gemini credentials first. If either provider fails, the agent falls back safely and still completes the run.

For deterministic local footage:

```powershell
python scripts\capture_demo.py
```

## Run The Backend

Hosted Cloud Run service:

```text
https://zerotouch-sre-971465910048.us-central1.run.app
```

Health check:

```powershell
Invoke-RestMethod -Method Get -Uri "https://zerotouch-sre-971465910048.us-central1.run.app/health"
```

Local backend:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Send an alert:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8080/alert `
  -ContentType "application/json" `
  -Body (Get-Content .\sample_alert.json -Raw)
```

The response includes:

- `status`
- `root_cause`
- `telemetry_mode`
- `mitigation`
- `post_mortem_path`
- `runbook_path`
- `trace_path`
- `billing`

## Environment

The app reads `.env` safely and never prints credentials.

Expected local variables:

```ini
DYNATRACE_API_KEY=<dynatrace-api-token>
DYNATRACE_URL=https://example.live.dynatrace.com
GEMINI_API_KEY=<gemini-api-key>
GCP_TOTAL_CREDIT_BUDGET_INR=25000
GCP_MAX_MONTHLY_BURN_LIMIT_INR=900
GCP_PROJECT_ID=zerotouch-sre-demo
```

Optional MCP command route:

```ini
DYNATRACE_MCP_COMMAND=python path/to/dynatrace_mcp_server.py
```

Testing override:

```ini
ZEROTOUCH_DISABLE_LIVE=1
```

## Safety Model

ZeroTouch SRE uses a simulation-first policy:

- Allowed actions:
  - `scale_service`
  - `rollback_release`
  - `open_incident_channel`
- Live production writes are disabled.
- Destructive actions require human approval.
- Unapproved actions raise a policy error.
- Each simulated action is written to `reports/mitigation_audit.jsonl`.

This is intentional. The demo shows useful autonomy without pretending that an unreviewed agent should have unrestricted production access.

## Generated Artifacts

After `python scripts\capture_demo.py --live`:

- `demo_response.json`: API-style response for the video.
- `post_mortem.md`: human-readable incident report.
- `runbook.json`: machine-readable incident artifact.
- `agent_trace.json`: inspectable perceive/retrieve/reason/plan/execute/synthesize trace.
- `reports/post_mortem_<timestamp>.md`: timestamped reports.
- `reports/runbook_<timestamp>.json`: timestamped runbooks.
- `reports/agent_trace_<timestamp>.json`: timestamped agent traces.
- `reports/mitigation_audit.jsonl`: append-only action audit log.

## Submission Readiness

```powershell
python scripts\capture_demo.py --live
python -m pytest -q
python -m compileall app tests scripts -q
python scripts\devpost_readiness.py
python scripts\cloud_run_preflight.py
```

Current readiness separates local package quality from external Devpost fields. The local project can be ready while these final public fields remain to be filled:

- Hosted Cloud Run URL
- Public repository URL
- Demo video URL

Use `DEVPOST_SUBMISSION.md` for the project write-up and `DEVPOST_FINAL_CHECKLIST.md` for the final recording/submission flow.

The hosted Cloud Run URL and smoke-test evidence are recorded in `CLOUD_RUN_DEPLOYMENT.md`.

## Cloud Run Deployment Sketch

```powershell
python scripts\cloud_run_preflight.py
gcloud auth login
gcloud config set project <PROJECT_ID>
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
gcloud run deploy zerotouch-sre --source . --region us-central1 --allow-unauthenticated
gcloud run services describe zerotouch-sre --region us-central1 --format="value(status.url)"
```

Set secrets and environment variables in Google Cloud. Do not commit `.env`.

## Verification Snapshot

Latest local verification:

```powershell
python -m pytest -q
# 11 passed

python scripts\devpost_readiness.py
# ready_for_devpost_packaging: true
```

## License

MIT. See `MIT-LICENSE.txt`.
