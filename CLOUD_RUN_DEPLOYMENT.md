# ZeroTouch SRE Cloud Run Deployment

## Hosted URL

https://zerotouch-sre-971465910048.us-central1.run.app

Health check:

```powershell
Invoke-RestMethod -Method Get -Uri "https://zerotouch-sre-971465910048.us-central1.run.app/health"
```

Alert demo:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "https://zerotouch-sre-971465910048.us-central1.run.app/alert" `
  -ContentType "application/json" `
  -Body (Get-Content .\sample_alert.json -Raw)
```

## Deployment Target

- Google Cloud project: `geminiliveagenthack`
- Region: `us-central1`
- Service: `zerotouch-sre`
- Latest verified revision: `zerotouch-sre-00002-zjd`
- Public ingress: enabled

## Runtime Secret Handling

The Cloud Run service references Secret Manager for provider keys:

- `DYNATRACE_API_KEY` -> `zerotouch-dynatrace-api-key`
- `GEMINI_API_KEY` -> `zerotouch-gemini-api-key`

Non-secret runtime settings are plain environment variables:

- `DYNATRACE_URL`
- `GCP_PROJECT_ID`
- `GCP_TOTAL_CREDIT_BUDGET_INR`
- `GCP_MAX_MONTHLY_BURN_LIMIT_INR`
- `ZEROTOUCH_DISABLE_LIVE`

## Verified Behavior

- `/health` returned `{"status":"ok","service":"zerotouch-sre"}`.
- `/alert` returned `ok: true`, `status: mitigated`, safe simulated mitigation actions, billing snapshot, `post_mortem_path`, `runbook_path`, and `trace_path`.
- Live-first runtime attempted provider access and completed with deterministic mock telemetry fallback when live Dynatrace evidence was unavailable.
