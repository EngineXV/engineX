"""Integration health checks for log monitor."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import is_mock_mode, load_config


def _get(url: str, headers: dict[str, str]) -> dict[str, Any]:
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read(500).decode("utf-8", errors="replace")
            return {"ok": True, "status": response.status, "body": body}
    except HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": str(exc)}
    except (URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def check_grafana() -> dict[str, Any]:
    cfg = load_config()
    if is_mock_mode(cfg):
        return {"ok": True, "mode": "mock", "message": "Grafana mock mode (env not configured)"}

    url = f"{cfg.grafana_url}/api/health"
    result = _get(url, {"Authorization": f"Bearer {cfg.grafana_token}"})
    result["service"] = "grafana"
    return result


def check_slack() -> dict[str, Any]:
    webhook = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook:
        return {"ok": False, "service": "slack", "error": "SLACK_WEBHOOK_URL not set"}

    payload = json.dumps({"text": "Engine log monitor health check (safe to ignore)"}).encode("utf-8")
    request = Request(
        webhook,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            return {"ok": response.status == 200, "service": "slack", "status": response.status}
    except HTTPError as exc:
        return {"ok": False, "service": "slack", "status": exc.code, "error": str(exc)}
    except (URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "service": "slack", "error": str(exc)}


def check_all(*, ping_slack: bool = False) -> dict[str, Any]:
    checks = {
        "grafana": check_grafana(),
    }
    if ping_slack:
        checks["slack"] = check_slack()

    ok = all(item.get("ok") for item in checks.values())
    return {"ok": ok, "checks": checks}
