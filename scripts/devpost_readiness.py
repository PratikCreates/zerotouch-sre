from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def exists(path: str) -> bool:
    return ROOT.joinpath(path).exists()


def read(path: str) -> str:
    target = ROOT.joinpath(path)
    if not target.exists():
        return ""
    return target.read_text(encoding="utf-8", errors="ignore")


def readiness() -> dict[str, object]:
    readme = read("README.md")
    devpost = read("DEVPOST_SUBMISSION.md")
    deployment = read("CLOUD_RUN_DEPLOYMENT.md")
    license_text = read("MIT-LICENSE.txt")
    status = read("HACKATHON_STATUS.md")
    prompt = read("PROMPT.txt")
    main_py = read("app/main.py")
    engine_py = read("app/engine.py")
    checks = [
        ("backend", "FastAPI app exists", exists("app/main.py") and '@app.post("/alert")' in main_py),
        ("agent", "Gemini role split documented", "gemini-3.5-flash" in readme and "gemini-3.1-pro" in readme),
        ("agent", "ADK adapter exists", exists("app/adk_adapter.py") and "GeminiADKAdapter" in engine_py),
        ("partner", "Dynatrace partner track represented", "Dynatrace" in readme and "DYNATRACE_API_KEY" in readme),
        ("mcp", "MCP client exists", exists("app/mcp_client.py") and "DYNATRACE_MCP_COMMAND" in readme),
        ("fallback", "Mock fallback exists", exists("app/mock_dynatrace.py") and "mock_dynatrace.py" in readme),
        ("budget", "Billing guard exists", exists("app/billing_guard.py") and "GCP_MAX_MONTHLY_BURN_LIMIT_INR" in readme),
        ("safety", "Safe action executor exists", exists("app/action_executor.py") and "mitigation_audit.jsonl" in readme),
        ("tests", "Tests exist", exists("tests/test_engine.py") and exists("tests/test_webhook.py")),
        ("license", "Open-source license exists", "MIT License" in license_text),
        ("cloud-run", "Container entrypoint exists", exists("Dockerfile") and "uvicorn" in read("Dockerfile")),
        ("cloud-run", "Deployment preflight exists", exists("scripts/cloud_run_preflight.py")),
        ("cloud-run", "Hosted deployment recorded", "https://zerotouch-sre-971465910048.us-central1.run.app" in deployment),
        ("sample", "Sample alert exists", exists("sample_alert.json")),
        ("report", "Sample post-mortem exists", exists("post_mortem.md") and "ZeroTouch SRE Post-Mortem" in read("post_mortem.md")),
        ("runbook", "Sample runbook exists", exists("runbook.json") and '"timeline"' in read("runbook.json")),
        ("trace", "Sample agent trace exists", exists("agent_trace.json") and '"stages"' in read("agent_trace.json")),
        ("demo", "Demo response exists", exists("demo_response.json") and '"trace_path"' in read("demo_response.json")),
        ("devpost", "Devpost draft exists", "What It Does" in devpost and "Demo Flow" in devpost),
        ("status", "Status log exists", "Definition of Done Evidence" in status),
        ("spec", "Original prompt retained", "definition of done" in prompt.lower()),
    ]
    results = [{"category": c, "check": label, "status": "ok" if ok else "missing"} for c, label, ok in checks]
    blockers = [item for item in results if item["status"] != "ok"]
    remaining_external_fields = [
        "Public repository URL after pushing to GitHub",
        "Demo video URL after recording/uploading ~3 minute demo",
    ]
    if "https://zerotouch-sre-971465910048.us-central1.run.app" not in deployment:
        remaining_external_fields.insert(0, "Hosted project URL after Cloud Run deploy")
    return {
        "project": "ZeroTouch SRE",
        "track": "Dynatrace partner track",
        "ready_for_devpost_packaging": not blockers,
        "hosted_url": "https://zerotouch-sre-971465910048.us-central1.run.app" if "https://zerotouch-sre-971465910048.us-central1.run.app" in deployment else None,
        "remaining_external_fields": remaining_external_fields,
        "checks": results,
    }


if __name__ == "__main__":
    data = readiness()
    print(json.dumps(data, indent=2))
    if not data["ready_for_devpost_packaging"]:
        raise SystemExit("ZeroTouch SRE readiness checks failed.")
