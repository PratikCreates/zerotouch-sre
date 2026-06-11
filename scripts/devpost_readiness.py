from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DOCS = ROOT / "_private" / "docs"
HOSTED_URL = "https://zerotouch-sre-971465910048.us-central1.run.app"
REPOSITORY_URL = "https://github.com/PratikCreates/zerotouch-sre"


def readiness() -> dict:
    required = {
        "README": ROOT / "README.md",
        "license": ROOT / "LICENSE",
        "dockerfile": ROOT / "Dockerfile",
        "sample alert": ROOT / "sample_alert.json",
        "submission draft": PRIVATE_DOCS / "DEVPOST_SUBMISSION.md",
        "final fields": PRIVATE_DOCS / "FINAL_SUBMISSION_FIELDS.md",
        "recording script": PRIVATE_DOCS / "DEMO_RECORDING_SCRIPT.md",
        "demo video script": ROOT / "scripts" / "create_demo_video.py",
    }
    missing = [label for label, path in required.items() if not path.exists()]
    remaining_external_fields: list[str] = []
    demo_video = ROOT / "demo_assets" / "zerotouch_sre_demo.mp4"
    if not demo_video.exists():
        remaining_external_fields.append("Demo video URL after uploading generated video")

    return {
        "ready_for_devpost_packaging": not missing,
        "track": "Dynatrace partner track",
        "hosted_url": HOSTED_URL,
        "repository_url": REPOSITORY_URL,
        "missing_local_artifacts": missing,
        "remaining_external_fields": remaining_external_fields,
    }


def main() -> None:
    print(json.dumps(readiness(), indent=2))


if __name__ == "__main__":
    main()
