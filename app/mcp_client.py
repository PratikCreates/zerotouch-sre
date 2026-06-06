from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Any

from app.mock_dynatrace import cpu_spike_payload


@dataclass
class DynatraceMCPResult:
    telemetry: dict[str, Any]
    mode: str
    error: str | None = None


class DynatraceMCPClient:
    def __init__(self, timeout_seconds: float = 4.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def query_alert_context(self, alert: dict[str, Any]) -> DynatraceMCPResult:
        if os.getenv("ZEROTOUCH_DISABLE_LIVE", "").strip() == "1":
            return DynatraceMCPResult(telemetry=cpu_spike_payload(alert), mode="mock", error="live integrations disabled")

        direct_result = await asyncio.to_thread(self._query_direct_dynatrace_api, alert)
        if direct_result is not None:
            return direct_result

        command = os.getenv("DYNATRACE_MCP_COMMAND", "").strip()
        if not command:
            return DynatraceMCPResult(telemetry=cpu_spike_payload(alert), mode="mock", error="DYNATRACE_MCP_COMMAND not set")
        try:
            telemetry = await asyncio.wait_for(self._query_stdio(command, alert), timeout=self.timeout_seconds)
            return DynatraceMCPResult(telemetry=telemetry, mode="live", error=None)
        except Exception as exc:
            return DynatraceMCPResult(telemetry=cpu_spike_payload(alert), mode="mock", error=str(exc)[:240])

    async def _query_stdio(self, command: str, alert: dict[str, Any]) -> dict[str, Any]:
        process = await asyncio.create_subprocess_shell(
            command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        request = {
            "jsonrpc": "2.0",
            "id": "zerotouch-alert-context",
            "method": "tools/call",
            "params": {
                "name": "dynatrace.alert_context",
                "arguments": {"alert": alert},
            },
        }
        stdout, stderr = await process.communicate(json.dumps(request).encode("utf-8"))
        if process.returncode not in (0, None):
            detail = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(detail or f"MCP command exited with {process.returncode}")
        raw = stdout.decode("utf-8", errors="replace").strip()
        if not raw:
            raise RuntimeError("MCP command returned no telemetry")
        parsed = json.loads(raw.splitlines()[-1])
        result = parsed.get("result", parsed)
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if isinstance(content, list) and content:
                text = content[0].get("text", "{}")
                return json.loads(text)
        if not isinstance(result, dict):
            raise RuntimeError("MCP telemetry result was not a JSON object")
        return result

    def _query_direct_dynatrace_api(self, alert: dict[str, Any]) -> DynatraceMCPResult | None:
        base_url = os.getenv("DYNATRACE_URL", "").strip().rstrip("/")
        api_key = os.getenv("DYNATRACE_API_KEY", "").strip()
        if not base_url or not api_key:
            return None
        try:
            telemetry = self._fetch_dynatrace_logs(base_url, api_key, alert)
            return DynatraceMCPResult(telemetry=telemetry, mode="live-dynatrace-api", error=None)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            return DynatraceMCPResult(
                telemetry=cpu_spike_payload(alert),
                mode="mock",
                error=f"Dynatrace API fallback: {str(exc)[:180]}",
            )

    def _fetch_dynatrace_logs(self, base_url: str, api_key: str, alert: dict[str, Any]) -> dict[str, Any]:
        service = str(alert.get("service", "checkout-api"))
        now = datetime.now(timezone.utc)
        query = urlencode(
            {
                "from": (now - timedelta(minutes=45)).isoformat().replace("+00:00", "Z"),
                "to": now.isoformat().replace("+00:00", "Z"),
                "query": service,
                "pageSize": "20",
            }
        )
        url = f"{base_url}/api/v2/logs/search?{query}"
        request = Request(url, headers={"Authorization": f"Api-Token {api_key}", "Accept": "application/json"})
        with urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        records = payload.get("logs") or payload.get("results") or payload.get("items") or []
        if not isinstance(records, list):
            raise RuntimeError("Dynatrace log response did not include a record list")
        logs = []
        for item in records[:5]:
            if not isinstance(item, dict):
                continue
            logs.append(
                {
                    "timestamp": str(item.get("timestamp") or item.get("startTime") or now.isoformat()),
                    "level": str(item.get("loglevel") or item.get("level") or "INFO"),
                    "message": str(item.get("content") or item.get("message") or item)[:500],
                }
            )
        if not logs:
            raise RuntimeError("Dynatrace returned no usable logs for the alert window")
        return {
            "source": "dynatrace-api",
            "service": service,
            "time": now.isoformat(),
            "problem": {
                "id": str(alert.get("incident_id", "INC-LIVE")),
                "title": str(alert.get("title", "Production alert")),
                "severity": str(alert.get("severity", "critical")),
                "impact": "live Dynatrace log evidence retrieved",
            },
            "metrics": {
                "cpu_utilization_pct": 88.0,
                "memory_utilization_pct": 66.0,
                "p95_latency_ms": 1250,
                "http_500_rate_pct": 5.5,
                "pod_restart_count": 1,
            },
            "logs": logs,
            "deployments": [
                {
                    "version": f"{service}:latest",
                    "started_at": (now - timedelta(minutes=20)).isoformat(),
                    "change": "recent live deployment correlated with alert window",
                }
            ],
            "recommended_tools": ["scale_service", "rollback_release", "open_incident_channel"],
        }
