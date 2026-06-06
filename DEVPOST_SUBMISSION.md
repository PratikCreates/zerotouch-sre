# ZeroTouch SRE Devpost Submission Draft

## Project Name

ZeroTouch SRE

## Hosted Project URL

https://zerotouch-sre-971465910048.us-central1.run.app

## Tagline

An autonomous SRE agent that turns a production alert into telemetry-backed diagnosis, simulated mitigation, and a post-mortem.

## What It Does

ZeroTouch SRE exposes a machine-to-machine FastAPI webhook at `POST /alert`. When a simulated production alert arrives, the backend normalizes the incident, tries to collect live Dynatrace evidence, falls back to deterministic mock telemetry if auth or MCP routing fails, reasons about root cause, plans a safe mitigation, runs every proposed action through a safe simulation allowlist, tracks estimated Gemini token burn, and writes both a detailed markdown post-mortem and a machine-readable incident runbook.

## How We Built It

- FastAPI backend for the webhook pipeline.
- Gemini Enterprise Agent Platform-style role split:
  - `gemini-3.5-flash` for perceive/reason/plan.
  - `gemini-3.1-pro` for post-mortem synthesis.
- Google ADK compatibility adapter that records runtime availability and model-role metadata in the agent trace.
- Dynatrace integration through an MCP-compatible client plus direct API fallback support.
- Budget guard that reads local GCP credit limits from `.env` without printing credentials.
- Safe action executor with allowlisted simulated mitigations and an append-only audit log.
- Deterministic tests that disable live calls and prove the full alert-to-report flow.
- Dockerfile for Cloud Run deployment.

## Google Cloud And Partner Services

- Google Gemini model roles are implemented in the engine and live Gemini REST synthesis is attempted when `GEMINI_API_KEY` is present.
- Dynatrace is the partner telemetry source. The app tries real credentials first and falls back autonomously to mock evidence when live access is unavailable.
- Cloud Run is the deployed target through the included Dockerfile.

## Impact

SRE teams need quick triage and consistent documentation during incidents. ZeroTouch SRE gives teams a safe first step toward autonomous operations: the agent can recommend and simulate mitigation without taking destructive production action, while preserving the evidence trail needed for review.

## What Makes It Unique

The project does not stop at chat-based diagnosis. It completes an operational loop: alert ingestion, telemetry lookup, reasoning, mitigation planning, action simulation, and post-mortem generation.

## Demo Flow

1. Open the hosted Cloud Run backend.
2. Send `sample_alert.json` to `POST /alert`.
3. Show the JSON response with root cause, telemetry mode, mitigation, runbook path, trace path, and billing snapshot.
4. Open `post_mortem.md`, `runbook.json`, and `agent_trace.json`.
5. Explain that live Dynatrace/Gemini are tried first, while fallback makes the demo resilient.
6. Use `scripts/capture_demo.py --live` to regenerate the same artifacts for the recording.

## Verification

```powershell
python -m pytest -q
python scripts\capture_demo.py --live
python scripts\devpost_readiness.py
```

## Remaining External Submission Fields

- Public repository URL after pushing this project.
- Demo video URL after recording the alert-to-post-mortem flow.
