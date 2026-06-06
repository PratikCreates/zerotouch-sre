# ZeroTouch SRE Demo Recording Script

Target length: 2.5 to 3 minutes.

## 0:00-0:20 Problem

Show the README headline and say:

> During incidents, SRE teams lose the first few minutes jumping between alerts, logs, dashboards, runbooks, and post-mortem notes. ZeroTouch SRE turns one alert into evidence-backed triage, safe mitigation, and an auditable report.

## 0:20-0:45 Architecture

Show the README architecture diagram.

Call out:

- FastAPI `POST /alert`
- Dynatrace live-first telemetry with MCP/direct API fallback
- `gemini-3.5-flash` role for perceive/reason/plan
- `gemini-3.1-pro` role for synthesis
- safe simulation action policy
- post-mortem, runbook, and agent trace outputs

## 0:45-1:20 Hosted Cloud Run

Run:

```powershell
Invoke-RestMethod -Method Get -Uri "https://zerotouch-sre-971465910048.us-central1.run.app/health"
```

Expected point:

> The backend is live on Cloud Run, not just running locally.

## 1:20-2:05 Alert To Mitigation

Run:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "https://zerotouch-sre-971465910048.us-central1.run.app/alert" `
  -ContentType "application/json" `
  -Body (Get-Content .\sample_alert.json -Raw)
```

Point out:

- `ok: true`
- `status: mitigated`
- root cause
- `telemetry_mode`
- safe simulated actions
- billing snapshot
- `post_mortem_path`
- `runbook_path`
- `trace_path`

Say:

> The demo attempted live provider access and completed safely with deterministic telemetry fallback when live evidence was unavailable. That keeps the agent reliable under auth or partner API issues.

## 2:05-2:35 Local Evidence Artifacts

Run locally:

```powershell
python scripts\capture_demo.py --live
```

Open:

- `post_mortem.md`
- `runbook.json`
- `agent_trace.json`

Point out:

- timeline
- root cause
- safe action audit
- model-role metadata
- budget guard

## 2:35-2:55 Quality Gate

Run:

```powershell
python -m pytest -q
python scripts\devpost_readiness.py
```

Say:

> The project has deterministic tests for the webhook, incident engine, action safety policy, deliverables, and Devpost readiness.

## 2:55-3:00 Close

Say:

> ZeroTouch SRE is a safe first step toward autonomous operations: the agent does the repetitive incident work, but destructive actions stay policy-gated and auditable.

## Suggested Social Post

Built ZeroTouch SRE for the Google Cloud Rapid Agent Hackathon: a Cloud Run SRE agent that turns one production alert into Dynatrace-backed triage, safe simulated mitigation, a post-mortem, a runbook, and an inspectable agent trace.

Live backend: https://zerotouch-sre-971465910048.us-central1.run.app
