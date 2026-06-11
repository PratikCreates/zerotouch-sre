from __future__ import annotations

import json
from pathlib import Path
from urllib.request import urlopen

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
HOSTED_URL = "https://zerotouch-sre-971465910048.us-central1.run.app"
REQUIRED_ENV = ["DYNATRACE_API_KEY", "DYNATRACE_URL", "GEMINI_API_KEY", "GCP_PROJECT_ID"]


def main() -> None:
    env = dotenv_values(ROOT / ".env")
    env_status = {}
    for name in REQUIRED_ENV:
        value = env.get(name)
        env_status[name] = "present" if value else "missing"
    with urlopen(f"{HOSTED_URL}/health", timeout=20) as response:
        health = json.loads(response.read().decode("utf-8"))

    print(
        json.dumps(
            {
                "hosted_url": HOSTED_URL,
                "health": health,
                "env": env_status,
                "secrets_redacted": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
