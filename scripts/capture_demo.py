from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.engine import ZeroTouchSREEngine


async def capture_demo(alert_path: Path, output_path: Path, live: bool) -> dict[str, Any]:
    if not live:
        os.environ["ZEROTOUCH_DISABLE_LIVE"] = "1"
    alert = json.loads(alert_path.read_text(encoding="utf-8"))
    engine = ZeroTouchSREEngine(write_root_samples=True)
    result = await engine.handle_alert(alert)
    response = {
        "ok": True,
        "incident_id": result.incident_id,
        "status": result.status,
        "root_cause": result.root_cause,
        "telemetry_mode": result.telemetry_mode,
        "mitigation": result.mitigation,
        "post_mortem_path": result.post_mortem_path,
        "runbook_path": result.runbook_path,
        "trace_path": result.trace_path,
        "billing": result.billing,
    }
    output_path.write_text(json.dumps(response, indent=2), encoding="utf-8")
    return response


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture a deterministic ZeroTouch SRE demo run.")
    parser.add_argument("--alert", default=str(ROOT / "sample_alert.json"))
    parser.add_argument("--output", default=str(ROOT / "demo_response.json"))
    parser.add_argument("--live", action="store_true", help="Try live Dynatrace/Gemini integrations before fallback.")
    args = parser.parse_args()

    response = asyncio.run(capture_demo(Path(args.alert), Path(args.output), live=args.live))
    print(json.dumps({
        "incident_id": response["incident_id"],
        "status": response["status"],
        "telemetry_mode": response["telemetry_mode"],
        "post_mortem_path": response["post_mortem_path"],
        "runbook_path": response["runbook_path"],
        "trace_path": response["trace_path"],
        "estimated_cost_inr": response["billing"]["estimated_cost_inr"],
    }, indent=2))


if __name__ == "__main__":
    main()
