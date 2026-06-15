"""Grafana Loki log fetcher."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import load_config
from .models import LogEntry

DEFAULT_KEYWORDS = ("error", "exception", "fatal", "panic")


def _keywords_from_env() -> tuple[str, ...]:
    return load_config().keywords


def _lookback_minutes() -> int:
    return load_config().lookback_minutes


def _mock_logs() -> list[LogEntry]:
    now = datetime.now(tz=UTC).isoformat()
    return [
        LogEntry(
            timestamp=now,
            service="payments-api",
            level="error",
            message="HTTP 503 upstream timeout contacting payment-gateway",
            trace_id="trace-mock-001",
        ),
        LogEntry(
            timestamp=now,
            service="auth-service",
            level="exception",
            message="NullPointerException in token validation handler",
            trace_id="trace-mock-002",
        ),
        LogEntry(
            timestamp=now,
            service="cron-reports",
            level="error",
            message="Failed to parse CSV row 42: invalid date format",
            trace_id="trace-mock-003",
        ),
    ]


def _build_logql(keywords: tuple[str, ...]) -> str:
    pattern = "|".join(re.escape(word) for word in keywords)
    return f'{{job=~".+"}} |~ "(?i)({pattern})"'


def _parse_loki_response(payload: dict[str, Any]) -> list[LogEntry]:
    entries: list[LogEntry] = []
    for stream in payload.get("data", {}).get("result", []):
        labels = stream.get("stream", {})
        service = (
            labels.get("service")
            or labels.get("app")
            or labels.get("job")
            or "unknown"
        )
        level = labels.get("level") or labels.get("severity") or "error"
        for value_pair in stream.get("values", []):
            if len(value_pair) < 2:
                continue
            ts_ns, line = value_pair[0], value_pair[1]
            try:
                ts_sec = int(ts_ns) / 1_000_000_000
                timestamp = datetime.fromtimestamp(ts_sec, tz=UTC).isoformat()
            except (TypeError, ValueError):
                timestamp = datetime.now(tz=UTC).isoformat()
            entries.append(
                LogEntry(
                    timestamp=timestamp,
                    service=service,
                    level=str(level).lower(),
                    message=str(line)[:2000],
                    labels={str(k): str(v) for k, v in labels.items()},
                    trace_id=labels.get("trace_id", labels.get("traceID", "")),
                )
            )
    return entries


def query_grafana_logs(
    minutes: int | None = None,
    keywords: list[str] | None = None,
) -> list[LogEntry]:
    """Fetch filtered logs from Grafana Loki or return mock data when unconfigured."""
    lookback = minutes or _lookback_minutes()
    kw = tuple(k.lower() for k in keywords) if keywords else _keywords_from_env()

    cfg = load_config()
    base_url = cfg.grafana_url
    token = cfg.grafana_token
    datasource_uid = cfg.grafana_datasource_uid

    if not base_url or not token or not datasource_uid:
        return _mock_logs()

    end = datetime.now(tz=UTC)
    start = end - timedelta(minutes=lookback)
    query = _build_logql(kw)

    params = urlencode(
        {
            "query": query,
            "start": int(start.timestamp() * 1_000_000_000),
            "end": int(end.timestamp() * 1_000_000_000),
            "limit": os.environ.get("LOG_MONITOR_QUERY_LIMIT", "200"),
        }
    )
    url = f"{base_url}/api/datasources/proxy/uid/{datasource_uid}/loki/api/v1/query_range?{params}"
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return _mock_logs()

    return _parse_loki_response(payload)
