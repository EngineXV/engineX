"""Outbound alert integrations."""

from __future__ import annotations

import base64
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import load_config
from .dedup_store import DedupStore


def _post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/json", **(headers or {})}
    request = Request(url, data=body, headers=req_headers, method="POST")
    try:
        with urlopen(request, timeout=15) as response:
            text = response.read().decode("utf-8")
            return {"ok": True, "status": response.status, "body": text[:500]}
    except HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": str(exc)}
    except (URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def _alert_cooldown_check(fingerprint: str) -> dict[str, Any] | None:
    if not fingerprint:
        return None
    cfg = load_config()
    store = DedupStore()
    if store.is_alert_on_cooldown(fingerprint, cfg.alert_cooldown_minutes):
        return {
            "ok": False,
            "skipped": True,
            "reason": f"alert cooldown ({cfg.alert_cooldown_minutes}m)",
            "fingerprint": fingerprint,
        }
    return None


def send_slack_alert(
    severity: str,
    title: str,
    body: str,
    fingerprint: str = "",
) -> dict[str, Any]:
    webhook = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook:
        return {"ok": False, "skipped": True, "reason": "SLACK_WEBHOOK_URL not set"}

    cooldown = _alert_cooldown_check(fingerprint)
    if cooldown:
        cooldown["channel"] = "slack"
        return cooldown

    emoji_map = {
        "SEVERE": ":rotating_light:",
        "HIGH": ":warning:",
        "MEDIUM": ":large_yellow_circle:",
    }
    emoji = emoji_map.get(severity, ":information_source:")
    payload = {
        "text": f"{emoji} *[{severity}] {title}*",
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{severity}* — {title}\n{body}"},
            }
        ],
    }
    result = _post_json(webhook, payload)
    result["channel"] = "slack"
    if result.get("ok") and fingerprint:
        DedupStore().mark_alert_sent(fingerprint, severity, "slack")
    return result


def send_pagerduty_alert(
    severity: str, title: str, body: str, fingerprint: str
) -> dict[str, Any]:
    routing_key = os.environ.get("PAGERDUTY_ROUTING_KEY", "")
    if not routing_key:
        return {"ok": False, "skipped": True, "reason": "PAGERDUTY_ROUTING_KEY not set"}
    if severity != "SEVERE":
        return {"ok": False, "skipped": True, "reason": "PagerDuty only for SEVERE"}

    cooldown = _alert_cooldown_check(fingerprint)
    if cooldown:
        cooldown["channel"] = "pagerduty"
        return cooldown

    payload = {
        "routing_key": routing_key,
        "event_action": "trigger",
        "dedup_key": fingerprint,
        "payload": {
            "summary": title,
            "severity": "critical",
            "source": "engine-log-monitor",
            "custom_details": {"body": body, "severity": severity},
        },
    }
    result = _post_json("https://events.pagerduty.com/v2/enqueue", payload)
    result["channel"] = "pagerduty"
    if result.get("ok") and fingerprint:
        DedupStore().mark_alert_sent(fingerprint, severity, "pagerduty")
    return result


def create_ticket(title: str, body: str, severity: str) -> dict[str, Any]:
    jira_url = os.environ.get("JIRA_URL", "").rstrip("/")
    jira_token = os.environ.get("JIRA_API_TOKEN", "")
    jira_email = os.environ.get("JIRA_EMAIL", "")
    project = os.environ.get("JIRA_PROJECT_KEY", "")

    if not all([jira_url, jira_token, jira_email, project]):
        return {
            "ok": False,
            "skipped": True,
            "reason": "Jira env vars not fully configured",
        }

    headers = {
        "Authorization": f"Basic {base64.b64encode(f'{jira_email}:{jira_token}'.encode()).decode('ascii')}",
        "Accept": "application/json",
    }
    payload = {
        "fields": {
            "project": {"key": project},
            "summary": f"[{severity}] {title}",
            "description": body,
            "issuetype": {"name": "Task"},
        }
    }
    result = _post_json(f"{jira_url}/rest/api/2/issue", payload, headers=headers)
    result["channel"] = "jira"
    return result
