"""Production readiness tests for log monitor agent."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from log_monitor.lib.alerts import send_slack_alert
from log_monitor.lib.config import validate_production_config
from log_monitor.lib.dedup_store import DedupStore
from log_monitor.tools import build_dispatch_plan


def test_validate_production_config_requires_grafana_when_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GRAFANA_URL", raising=False)
    monkeypatch.delenv("LOG_MONITOR_ALLOW_MOCK", raising=False)
    errors = validate_production_config(require_live=True)
    assert any("GRAFANA" in err for err in errors)


def test_validate_production_config_allows_mock_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_MONITOR_ALLOW_MOCK", "1")
    errors = validate_production_config(require_live=True)
    assert errors == []


def test_build_dispatch_plan_skips_human_review_in_daemon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOG_MONITOR_DAEMON", "1")
    incidents = json.dumps(
        [
            {"severity": "MEDIUM", "service": "api", "message": "slow query"},
        ]
    )
    plan = build_dispatch_plan(incidents)
    assert plan["needs_human_review"] is False
    assert plan["daemon_mode"] is True
    assert len(json.loads(plan["daemon_medium_json"])) == 1


def test_alert_cooldown_blocks_repeat_slack(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store_path = Path(tmp) / "seen.json"
        monkeypatch.setattr(
            "log_monitor.lib.alerts.DedupStore",
            lambda: DedupStore(store_path),
        )
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://example.com/webhook")
        monkeypatch.setenv("LOG_MONITOR_ALERT_COOLDOWN_MINUTES", "30")

        store = DedupStore(store_path)
        store.mark_alert_sent("fp-test", "HIGH", "slack")

        result = send_slack_alert("HIGH", "title", "body", fingerprint="fp-test")
        assert result.get("skipped") is True
        assert "cooldown" in result.get("reason", "")
