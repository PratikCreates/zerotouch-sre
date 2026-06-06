# ZeroTouch SRE Walkthrough

This walkthrough shows how to validate ZeroTouch SRE from the hosted Cloud Run service and from a local development environment.

## 1. Confirm The Hosted Service

Open the landing page:

```text
https://zerotouch-sre-971465910048.us-central1.run.app/
```

The page links to the guided incident review, API docs, health check, and source repository.

Run:

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "https://zerotouch-sre-971465910048.us-central1.run.app/health"
```

Expected response:

```json
{
  "status": "ok",
  "service": "zerotouch-sre"
}
```

This proves the Cloud Run service is reachable and the FastAPI app has started correctly.

## 2. Send A Production Alert

Incident sandbox:

```text
https://zerotouch-sre-971465910048.us-central1.run.app/demo
```

That endpoint runs the included checkout incident through the full backend loop.

Manual API path:

Run:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "https://zerotouch-sre-971465910048.us-central1.run.app/alert" `
  -ContentType "application/json" `
  -Body (Get-Content .\sample_alert.json -Raw)
```

The response should include:

- `ok: true`
- `status: mitigated`
- `root_cause`
- `telemetry_mode`
- `telemetry`
- `mitigation`
- `post_mortem_path`
- `runbook_path`
- `trace_path`
- `billing`

The hosted service may return `telemetry_mode: mock` when live Dynatrace evidence is unavailable. That is expected behavior: the telemetry client attempts live evidence first, then falls back to deterministic incident evidence so the workflow still completes.

## 3. Review The Mitigation

The `mitigation` object contains the action plan. The current safety policy permits only:

- `scale_service`
- `rollback_release`
- `open_incident_channel`

Each action is reported as `simulated_success`. The service does not perform destructive production writes.

## 4. Run Locally

Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start the API:

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

## 5. Run Quality Checks

```powershell
python -m compileall app -q
```

This confirms the public application package compiles cleanly. A practical hosted check is:

```powershell
$response = Invoke-RestMethod `
  -Method Post `
  -Uri "https://zerotouch-sre-971465910048.us-central1.run.app/alert" `
  -ContentType "application/json" `
  -Body (Get-Content .\sample_alert.json -Raw)

$response | Select-Object ok,status,telemetry_mode,incident_id
$response.telemetry
```

That end-to-end check validates the hosted webhook, incident loop, mitigation policy, and artifact generation path.

## 6. Deployment Notes

The public Cloud Run deployment uses:

- Project: `geminiliveagenthack`
- Region: `us-central1`
- Service: `zerotouch-sre`
- Provider keys: Secret Manager references

The repository intentionally excludes local `.env`, generated reports, private validation assets, and operator-only notes.

## 7. Connect

[Pratik Shah](https://www.linkedin.com/in/pratikcreates)
