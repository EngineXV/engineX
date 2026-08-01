"""Lightweight Prometheus-style metrics for the Engine dashboard."""

from __future__ import annotations

import threading
import time
from typing import Any

_lock = threading.Lock()
_counters: dict[str, float] = {
    "engine_sessions_active": 0.0,
    "engine_sessions_created_total": 0.0,
    "engine_executions_started_total": 0.0,
    "engine_executions_completed_total": 0.0,
    "engine_executions_failed_total": 0.0,
}
_gauges: dict[str, float] = {
    "engine_uptime_seconds": 0.0,
    "enginex_run_cost_usd": 0.0,
    "enginex_node_tokens": 0.0,
}
_start_time = time.time()


def inc(name: str, amount: float = 1.0) -> None:
    with _lock:
        _counters[name] = _counters.get(name, 0.0) + amount


def set_gauge(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    with _lock:
        if labels:
            label_key = ",".join(f"{key}={value}" for key, value in sorted(labels.items()))
            _gauges[f"{name}{{{label_key}}}"] = value
            return
        _gauges[name] = value


def observe_session_count(count: int) -> None:
    set_gauge("engine_sessions_active", float(count))


def prometheus_text() -> str:
    with _lock:
        lines: list[str] = []
        uptime = time.time() - _start_time
        lines.append("# HELP engine_uptime_seconds Process uptime in seconds")
        lines.append("# TYPE engine_uptime_seconds gauge")
        lines.append(f"engine_uptime_seconds {uptime:.3f}")
        for name, value in sorted(_gauges.items()):
            if name == "engine_uptime_seconds":
                continue
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value:.0f}")
        for name, value in sorted(_counters.items()):
            metric_type = "counter" if name.endswith("_total") else "gauge"
            lines.append(f"# TYPE {name} {metric_type}")
            lines.append(f"{name} {value:.0f}")
        return "\n".join(lines) + "\n"


def snapshot() -> dict[str, Any]:
    with _lock:
        return {
            "counters": dict(_counters),
            "gauges": {**_gauges, "engine_uptime_seconds": time.time() - _start_time},
        }
