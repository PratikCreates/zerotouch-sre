# ZeroTouch SRE Final Devpost Checklist

Use this after the local build is green.

## Required Devpost Fields

- Project name: `ZeroTouch SRE`
- Track: `Dynatrace`
- Hosted project URL: `https://zerotouch-sre-971465910048.us-central1.run.app`
- Public repository URL: push this project to a public GitHub repository with `MIT-LICENSE.txt` visible at the top level.
- Demo video URL: upload `demo_assets\zerotouch_sre_demo.mp4`, or record a narrated take using `DEMO_RECORDING_SCRIPT.md`.
- Description: use `DEVPOST_SUBMISSION.md`.

## Demo Video Script

Use `DEMO_RECORDING_SCRIPT.md` as the polished recording script. The abbreviated flow is:

1. Show the Devpost problem: on-call SRE teams need fast triage and reliable post-mortems.
2. Show the architecture in `README.md`.
3. Generate clean demo artifacts with:

```powershell
python scripts\capture_demo.py --live
```

4. Start the backend with:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

5. Send `sample_alert.json` to `/alert`, or show the already captured `demo_response.json`.
6. Show response fields:
   - `telemetry_mode`
   - `root_cause`
   - `mitigation`
   - `billing`
   - `post_mortem_path`
   - `runbook_path`
   - `trace_path`
7. Open `post_mortem.md`, `runbook.json`, and `agent_trace.json`.
8. Explain live-first behavior: Dynatrace/Gemini are attempted with real credentials; auth or API issues fall back safely.
9. Show `python -m pytest -q` passing.

## Generated Demo Asset

A silent slide-based MP4 is generated locally at:

```powershell
demo_assets\zerotouch_sre_demo.mp4
```

Regenerate it with:

```powershell
python scripts\create_demo_video.py
```

Upload the MP4 to YouTube, Loom, Google Drive, or another public video host, then paste that public URL into Devpost.

## GitHub Publishing

GitHub CLI is installed, but authentication is required before I can push from this machine:

```powershell
gh auth login
gh repo create zerotouch-sre --public --source . --remote origin --push
```

## Local Evidence Commands

```powershell
python -m pytest -q
python -m compileall app tests -q
python scripts\capture_demo.py --live
python scripts\devpost_readiness.py
python scripts\cloud_run_preflight.py
```

## Cloud Run Evidence

Deployment and smoke-test notes are in `CLOUD_RUN_DEPLOYMENT.md`.

```powershell
Invoke-RestMethod -Method Get -Uri "https://zerotouch-sre-971465910048.us-central1.run.app/health"
Invoke-RestMethod -Method Post -Uri "https://zerotouch-sre-971465910048.us-central1.run.app/alert" -ContentType "application/json" -Body (Get-Content .\sample_alert.json -Raw)
```

## Cloud Run Redeploy Sketch

This machine currently needs the Google Cloud SDK (`gcloud`) available on `PATH` before deployment. The preflight helper checks that without printing secrets:

```powershell
python scripts\cloud_run_preflight.py
```

If `gcloud_available` is `false`, install the Google Cloud SDK, restart PowerShell, then rerun the preflight.

```powershell
gcloud auth login
gcloud config set project <PROJECT_ID>
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
gcloud run deploy zerotouch-sre --source . --region us-central1 --allow-unauthenticated
gcloud run services describe zerotouch-sre --region us-central1 --format="value(status.url)"
```

Set secrets/environment variables in Google Cloud, not in the repository. Use the returned service URL plus `/health` as the hosted project URL.
