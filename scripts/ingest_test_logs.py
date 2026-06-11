from __future__ import annotations

import os
import json
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    load_dotenv(os.path.join(ROOT, ".env"))
    base_url = os.getenv("DYNATRACE_URL", "").strip().rstrip("/")
    api_key = os.getenv("DYNATRACE_API_KEY", "").strip()

    if not base_url or not api_key:
        print("Error: DYNATRACE_URL or DYNATRACE_API_KEY not set in .env")
        return

    url = f"{base_url}/api/v2/logs/ingest"
    print(f"Ingesting logs to: {url}")

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload = [
        {
            "timestamp": now,
            "status": "error",
            "content": "checkout-api worker timeout while waiting for payment dependency",
            "service": "checkout-api",
        },
        {
            "timestamp": now,
            "status": "warn",
            "content": "horizontal pod autoscaler at max replicas; CPU target exceeded",
            "service": "checkout-api",
        },
        {
            "timestamp": now,
            "status": "error",
            "content": "HTTP 500 spike correlated with release checkout-api:2026.06.07-rc2",
            "service": "checkout-api",
        },
    ]

    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Api-Token {api_key}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            status = response.status
            print(f"Response status: {status}")
            if status == 204:
                print("Successfully ingested 3 test logs into Dynatrace!")
            else:
                print(f"Unexpected success code: {status}")
    except HTTPError as exc:
        print(f"HTTP Error: {exc.code} - {exc.reason}")
        print("Response body:")
        print(exc.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        print(f"Unexpected error: {exc}")


if __name__ == "__main__":
    main()
