"""Context enrichment: ownership, deploys, metrics."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def _catalog_path() -> Path | None:
    raw = os.environ.get("SERVICE_CATALOG_PATH", "")
    if not raw:
        default = Path.home() / ".engine" / "log_monitor" / "service_catalog.json"
        return default if default.exists() else None
    path = Path(raw).expanduser()
    return path if path.exists() else None


def get_service_owner(service: str) -> str:
    path = _catalog_path()
    if not path:
        customer_facing = {"payments-api", "auth-service", "checkout", "api-gateway"}
        if service in customer_facing:
            return "@platform-oncall"
        return "@backend-team"
    try:
        with open(path, encoding="utf-8") as handle:
            catalog = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return "@backend-team"
    entry = catalog.get(service, {})
    return str(entry.get("owner", "@backend-team"))


def get_recent_deploy_note(service: str) -> str:
    deploy_file = Path.home() / ".engine" / "log_monitor" / "deploy_events.json"
    if not deploy_file.exists():
        return "No recent deploy data configured"
    try:
        with open(deploy_file, encoding="utf-8") as handle:
            events: list[dict[str, Any]] = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return "Deploy history unavailable"

    cutoff = datetime.now(tz=UTC) - timedelta(hours=2)
    for event in reversed(events):
        if event.get("service") != service:
            continue
        ts_raw = event.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts >= cutoff:
            version = event.get("version", "unknown")
            return f"Deploy {version} within last 2h"
    return "No deploy in last 2h"


def get_metric_note(service: str, error_count: int) -> str:
    if error_count >= 20:
        return f"Error burst: {error_count} matching logs in window"
    if error_count >= 5:
        return f"Elevated errors: {error_count} in window"
    return f"{error_count} matching log(s) in window"
