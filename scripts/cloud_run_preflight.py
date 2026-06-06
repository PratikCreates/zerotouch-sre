from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
SERVICE = "zerotouch-sre"
REGION = os.getenv("CLOUD_RUN_REGION", "us-central1")
DEFAULT_DEPLOY_PROJECT = "geminiliveagenthack"
HOSTED_URL = "https://zerotouch-sre-971465910048.us-central1.run.app"


def env_keys() -> dict[str, str]:
    values = dotenv_values(ROOT / ".env")
    keys = {
        "GCP_PROJECT_ID": values.get("GCP_PROJECT_ID", ""),
        "DYNATRACE_URL": values.get("DYNATRACE_URL", ""),
        "DYNATRACE_API_KEY": values.get("DYNATRACE_API_KEY", ""),
        "GEMINI_API_KEY": values.get("GEMINI_API_KEY", ""),
        "GCP_TOTAL_CREDIT_BUDGET_INR": values.get("GCP_TOTAL_CREDIT_BUDGET_INR", ""),
        "GCP_MAX_MONTHLY_BURN_LIMIT_INR": values.get("GCP_MAX_MONTHLY_BURN_LIMIT_INR", ""),
    }
    return {name: "present" if value else "missing" for name, value in keys.items()}


def command_available(command: str) -> bool:
    return gcloud_path(command) is not None


def gcloud_path(command: str = "gcloud") -> str | None:
    from shutil import which

    found = which(command)
    if found:
        return found
    if command != "gcloud":
        return None
    candidates = [
        Path(os.getenv("LOCALAPPDATA", "")) / "Google" / "Cloud SDK" / "google-cloud-sdk" / "bin" / "gcloud.cmd",
        Path("C:/Program Files/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"),
        Path("C:/Program Files (x86)/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def current_gcloud_project() -> str:
    executable = gcloud_path()
    if not executable:
        return ""
    try:
        completed = subprocess.run(
            [executable, "config", "get-value", "project"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    value = completed.stdout.strip()
    return "" if value == "(unset)" else value


def preflight() -> dict[str, object]:
    project_from_env = dotenv_values(ROOT / ".env").get("GCP_PROJECT_ID", "")
    active_project = current_gcloud_project()
    project = os.getenv("CLOUD_RUN_PROJECT_ID") or DEFAULT_DEPLOY_PROJECT or active_project or project_from_env or "<PROJECT_ID>"
    commands = [
        "gcloud auth login",
        f"gcloud config set project {project}",
        "gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com",
        (
            f"gcloud run deploy {SERVICE} --source . --region {REGION} "
            "--allow-unauthenticated --port 8080 "
            "--set-env-vars ZEROTOUCH_DISABLE_LIVE=0"
        ),
        f"gcloud run services describe {SERVICE} --region {REGION} --format=\"value(status.url)\"",
    ]
    return {
        "project": SERVICE,
        "hosted_url": HOSTED_URL,
        "cloud_run_region": REGION,
        "gcloud_available": command_available("gcloud"),
        "gcloud_path": gcloud_path(),
        "dockerfile_present": (ROOT / "Dockerfile").exists(),
        "required_env": env_keys(),
        "active_gcloud_project": active_project or None,
        "project_id_from_env": project_from_env or None,
        "deploy_project": project,
        "deploy_commands": commands,
        "notes": [
            "This script never prints credential values.",
            "Set secrets in Google Cloud or environment variables before deploying a live integration.",
            "Use the printed service URL plus /health as the hosted project URL.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(preflight(), indent=2))
