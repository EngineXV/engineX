"""Agent tools for log monitor integrations."""

from __future__ import annotations

import json
import os
from typing import Any

from engine.runner.tool_registry import tool

from log_monitor.lib.alerts import create_ticket, send_pagerduty_alert, send_slack_alert
from log_monitor.lib.config import validate_production_config
from log_monitor.lib.dedup_store import DedupStore
from log_monitor.lib.health import check_all
from log_monitor.lib.pipeline import run_monitor_tick


def _is_daemon_mode() -> bool:
    return os.environ.get("LOG_MONITOR_DAEMON", "").lower() in {"1", "true", "yes"}


@tool(description="Validate production config and integration health before monitoring.")
def preflight_check(require_live: bool = False) -> dict[str, Any]:
    errors = validate_production_config(require_live=require_live)
    health = check_all(ping_slack=False)
    return {
        "ok": not errors and health.get("ok", False),
        "errors": errors,
        "health": health,
        "daemon_mode": _is_daemon_mode(),
    }


@tool(description="Run one monitoring tick: Grafana fetch, dedup, and rule-based scoring.")
def run_log_monitor_pipeline() -> dict[str, Any]:
    return run_monitor_tick()


@tool(description="Send a Slack alert for an incident.")
def notify_slack(severity: str, title: str, body: str, fingerprint: str = "") -> dict[str, Any]:
    return send_slack_alert(severity, title, body, fingerprint=fingerprint)


@tool(description="Trigger PagerDuty for SEVERE incidents.")
def notify_pagerduty(severity: str, title: str, body: str, fingerprint: str) -> dict[str, Any]:
    return send_pagerduty_alert(severity, title, body, fingerprint)


@tool(description="Create a Jira ticket for an incident.")
def create_incident_ticket(title: str, body: str, severity: str) -> dict[str, Any]:
    return create_ticket(title, body, severity)


@tool(description="Record learning outcome for fingerprint tuning and mute window.")
def record_learning_outcome(
    fingerprint: str,
    severity: str,
    action: str,
    human_override: str = "",
) -> dict[str, Any]:
    store = DedupStore()
    store.record_outcome(fingerprint, severity, action, human_override)
    return {"ok": True, "fingerprint": fingerprint, "action": action}


@tool(description="Parse incidents JSON and return dispatch plan with alert targets.")
def build_dispatch_plan(incidents_json: str) -> dict[str, Any]:
    incidents: list[dict[str, Any]] = json.loads(incidents_json or "[]")
    severe_high: list[dict[str, Any]] = []
    medium: list[dict[str, Any]] = []
    low: list[dict[str, Any]] = []

    for item in incidents:
        severity = str(item.get("severity", "LOW")).upper()
        if severity in {"SEVERE", "HIGH"}:
            severe_high.append(item)
        elif severity == "MEDIUM":
            medium.append(item)
        else:
            low.append(item)

    daemon = _is_daemon_mode()
    return {
        "severe_high_json": json.dumps(severe_high),
        "medium_json": json.dumps(medium),
        "low_json": json.dumps(low),
        "needs_human_review": bool(medium) and not daemon,
        "daemon_medium_json": json.dumps(medium) if daemon else "[]",
        "alert_count": len(severe_high),
        "ticket_count": len(incidents),
        "daemon_mode": daemon,
    }
