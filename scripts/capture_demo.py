from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
HOSTED_URL = "https://zerotouch-sre-971465910048.us-central1.run.app"


def load_payload() -> dict:
    return json.loads((ROOT / "sample_alert.json").read_text(encoding="utf-8"))


def post_alert(url: str, payload: dict) -> dict:
    request = Request(
        f"{url.rstrip('/')}/alert",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture ZeroTouch SRE sample incident artifacts.")
    parser.add_argument("--live", action="store_true", help="Use the hosted Cloud Run service.")
    parser.add_argument("--url", default=HOSTED_URL, help="Base URL for the running service.")
    args = parser.parse_args()

    payload = load_payload()
    result = post_alert(args.url if args.live else "http://127.0.0.1:8080", payload)

    (ROOT / "demo_response.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    trace_path = result.get("trace_path")
    if trace_path:
        (ROOT / "agent_trace.json").write_text(
            json.dumps({"captured_from": args.url if args.live else "local", "trace_path": trace_path, "response": result}, indent=2),
            encoding="utf-8",
        )

    print(json.dumps({"ok": result.get("ok"), "incident_id": result.get("incident_id"), "status": result.get("status")}, indent=2))


if __name__ == "__main__":
    main()
