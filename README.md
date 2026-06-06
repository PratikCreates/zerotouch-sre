# ZeroTouch SRE

Autonomous incident triage and mitigation planning for production SRE teams.

ZeroTouch SRE is a FastAPI backend that receives a production alert, gathers telemetry, identifies a likely root cause, runs proposed actions through a safe simulation policy, and produces incident artifacts for review. It is designed for teams that want agentic operations without giving an unreviewed agent destructive production access.

![Hosted health check](assets/screenshots/01-health-check.png)

## Live Demo

- Hosted backend: [https://zerotouch-sre-971465910048.us-central1.run.app](https://zerotouch-sre-971465910048.us-central1.run.app)
- Health check: [https://zerotouch-sre-971465910048.us-central1.run.app/health](https://zerotouch-sre-971465910048.us-central1.run.app/health)

## What It Does

1. Accepts an incident alert at `POST /alert`.
2. Normalizes the alert into an incident record.
3. Attempts live Dynatrace telemetry through deployed credentials.
4. Falls back to deterministic telemetry if live evidence is unavailable.
5. Produces root-cause reasoning and a mitigation plan.
6. Executes only allowlisted simulated mitigation actions.
7. Returns paths for a post-mortem, machine-readable runbook, and agent trace.
8. Tracks estimated token burn against configured budget guardrails.

![Alert response](assets/screenshots/02-alert-result.png)

## Why It Matters

The first minutes of an outage are noisy: alerts, dashboards, runbooks, chat threads, and incomplete context all compete for attention. ZeroTouch SRE turns that early incident window into a structured operational loop. It gives small teams a consistent first pass at triage, a safe mitigation proposal, and reusable documentation without pretending that production control should be handed away blindly.

The project is built around three practical principles:

- **Action over chat**: the service completes a webhook-to-artifact workflow instead of only answering a question.
- **Evidence before action**: telemetry is gathered before root-cause reasoning and mitigation planning.
- **Human control by default**: production-affecting actions are simulated and allowlisted.

## Architecture

![Operational loop](assets/screenshots/03-architecture-loop.png)

The backend follows a controlled incident loop:

- **Webhook**: `app/main.py` exposes `/health` and `/alert`.
- **Telemetry**: `app/mcp_client.py` attempts Dynatrace evidence and falls back deterministically.
- **Reasoning**: `app/engine.py` performs the perceive, reason, plan, execute, synthesize flow.
- **Safety**: `app/action_executor.py` enforces an allowlist and writes an audit trail.
- **Budgeting**: `app/billing_guard.py` estimates usage and blocks excessive burn.
- **Runtime metadata**: `app/adk_adapter.py` records Google ADK availability and model-role metadata.

## Public API

### Health

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "https://zerotouch-sre-971465910048.us-central1.run.app/health"
```

Example response:

```json
{
  "status": "ok",
  "service": "zerotouch-sre"
}
```

### Alert

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "https://zerotouch-sre-971465910048.us-central1.run.app/alert" `
  -ContentType "application/json" `
  -Body (Get-Content .\sample_alert.json -Raw)
```

Key response fields:

- `ok`
- `incident_id`
- `status`
- `root_cause`
- `mitigation`
- `telemetry_mode`
- `post_mortem_path`
- `runbook_path`
- `trace_path`
- `billing`

## Safety Model

ZeroTouch SRE is intentionally simulation-first.

Allowed actions:

- `scale_service`
- `rollback_release`
- `open_incident_channel`

The action executor rejects unapproved or destructive actions. This keeps the agent useful during incident triage while preserving human control over production changes.

## Local Setup

Prerequisites:

- Python 3.11+
- `pip`

Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run locally:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Send a local alert:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8080/alert" `
  -ContentType "application/json" `
  -Body (Get-Content .\sample_alert.json -Raw)
```

## Configuration

Runtime configuration is read from environment variables:

```ini
DYNATRACE_URL=https://example.live.dynatrace.com
DYNATRACE_API_KEY=<dynatrace-api-token>
GEMINI_API_KEY=<gemini-api-key>
GCP_PROJECT_ID=<google-cloud-project-id>
GCP_TOTAL_CREDIT_BUDGET_INR=25000
GCP_MAX_MONTHLY_BURN_LIMIT_INR=900
```

For deterministic local runs:

```ini
ZEROTOUCH_DISABLE_LIVE=1
```

Never commit `.env` files. The deployed Cloud Run service uses Secret Manager for provider keys.

## Verification

```powershell
python -m compileall app -q
```

Current package status:

- FastAPI backend implemented.
- Cloud Run deployment verified.
- `/health` and `/alert` smoke-tested.
- Secret-backed provider keys configured in Cloud Run.
- Local verification completed successfully.

## Repository Layout

```text
.
|-- app/
|   |-- action_executor.py
|   |-- adk_adapter.py
|   |-- billing_guard.py
|   |-- engine.py
|   |-- main.py
|   |-- mcp_client.py
|   `-- mock_dynatrace.py
|-- assets/
|   `-- screenshots/
|-- Dockerfile
|-- LICENSE
|-- README.md
|-- WALKTHROUGH.md
|-- requirements.txt
`-- sample_alert.json
```

## Walkthrough

See [WALKTHROUGH.md](WALKTHROUGH.md) for a step-by-step operational walkthrough with commands and expected outputs.

## License

MIT. See [LICENSE](LICENSE).

## Connect

[Pratik Shah](https://www.linkedin.com/in/pratikcreates)
