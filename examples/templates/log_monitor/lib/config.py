"""Log monitor configuration and production validation."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LogMonitorConfig:
    grafana_url: str
    grafana_token: str
    grafana_datasource_uid: str
    slack_webhook_url: str
    pagerduty_routing_key: str
    jira_url: str
    jira_email: str
    jira_token: str
    jira_project: str
    lookback_minutes: int
    mute_minutes: int
    alert_cooldown_minutes: int
    keywords: tuple[str, ...]
    daemon_mode: bool
    allow_mock: bool


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def load_config() -> LogMonitorConfig:
    keywords_raw = os.environ.get("LOG_MONITOR_KEYWORDS", "error,exception,fatal,panic")
    keywords = tuple(part.strip().lower() for part in keywords_raw.split(",") if part.strip())
    return LogMonitorConfig(
        grafana_url=os.environ.get("GRAFANA_URL", "").rstrip("/"),
        grafana_token=os.environ.get("GRAFANA_API_TOKEN", ""),
        grafana_datasource_uid=os.environ.get("GRAFANA_DATASOURCE_UID", ""),
        slack_webhook_url=os.environ.get("SLACK_WEBHOOK_URL", ""),
        pagerduty_routing_key=os.environ.get("PAGERDUTY_ROUTING_KEY", ""),
        jira_url=os.environ.get("JIRA_URL", "").rstrip("/"),
        jira_email=os.environ.get("JIRA_EMAIL", ""),
        jira_token=os.environ.get("JIRA_API_TOKEN", ""),
        jira_project=os.environ.get("JIRA_PROJECT_KEY", ""),
        lookback_minutes=_int_env("LOG_MONITOR_LOOKBACK_MINUTES", 1),
        mute_minutes=_int_env("LOG_MONITOR_MUTE_MINUTES", 30),
        alert_cooldown_minutes=_int_env("LOG_MONITOR_ALERT_COOLDOWN_MINUTES", 15),
        keywords=keywords or ("error", "exception", "fatal", "panic"),
        daemon_mode=os.environ.get("LOG_MONITOR_DAEMON", "").lower() in {"1", "true", "yes"},
        allow_mock=os.environ.get("LOG_MONITOR_ALLOW_MOCK", "").lower() in {"1", "true", "yes"},
    )


def is_mock_mode(config: LogMonitorConfig | None = None) -> bool:
    cfg = config or load_config()
    if cfg.allow_mock:
        return True
    return not all([cfg.grafana_url, cfg.grafana_token, cfg.grafana_datasource_uid])


def validate_production_config(*, require_live: bool = False) -> list[str]:
    """Return list of configuration errors (empty means OK)."""
    cfg = load_config()
    errors: list[str] = []

    if is_mock_mode(cfg):
        if require_live and not cfg.allow_mock:
            errors.append(
                "Live mode required: set GRAFANA_URL, GRAFANA_API_TOKEN, "
                "GRAFANA_DATASOURCE_UID (or LOG_MONITOR_ALLOW_MOCK=1 for dev)"
            )
        return errors

    if not cfg.grafana_url:
        errors.append("GRAFANA_URL is required")
    if not cfg.grafana_token:
        errors.append("GRAFANA_API_TOKEN is required")
    if not cfg.grafana_datasource_uid:
        errors.append("GRAFANA_DATASOURCE_UID is required")
    if not cfg.slack_webhook_url:
        errors.append("SLACK_WEBHOOK_URL is required for production alerting")

    llm_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not llm_key:
        errors.append("ANTHROPIC_API_KEY or OPENAI_API_KEY is required for LLM triage nodes")

    return errors
