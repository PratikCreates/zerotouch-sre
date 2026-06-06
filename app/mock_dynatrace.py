from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def cpu_spike_payload(alert: dict[str, Any]) -> dict[str, Any]:
    service = str(alert.get("service", "checkout-api"))
    return {
        "source": "mock-dynatrace",
        "fallback_reason": "live MCP unavailable or not configured",
        "service": service,
        "time": datetime.now(timezone.utc).isoformat(),
        "problem": {
            "id": str(alert.get("incident_id", "INC-LOCAL-001")),
            "title": str(alert.get("title", "CPU saturation with elevated HTTP 500s")),
            "severity": str(alert.get("severity", "critical")),
            "impact": "customer checkout latency and intermittent failed requests",
        },
        "metrics": {
            "cpu_utilization_pct": 94.7,
            "memory_utilization_pct": 71.2,
            "p95_latency_ms": 1840,
            "http_500_rate_pct": 7.8,
            "pod_restart_count": 3,
        },
        "logs": [
            {
                "timestamp": "2026-06-07T00:12:20Z",
                "level": "ERROR",
                "message": "checkout-api worker timeout while waiting for payment dependency",
            },
            {
                "timestamp": "2026-06-07T00:13:03Z",
                "level": "WARN",
                "message": "horizontal pod autoscaler at max replicas; CPU target exceeded",
            },
            {
                "timestamp": "2026-06-07T00:13:44Z",
                "level": "ERROR",
                "message": "HTTP 500 spike correlated with release checkout-api:2026.06.07-rc2",
            },
        ],
        "deployments": [
            {
                "version": "checkout-api:2026.06.07-rc2",
                "started_at": "2026-06-07T00:03:00Z",
                "change": "payment retry loop changed from capped to unbounded",
            }
        ],
        "recommended_tools": ["scale_service", "rollback_release", "open_incident_channel"],
    }
