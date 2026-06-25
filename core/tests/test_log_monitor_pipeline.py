"""Tests for log monitor pipeline (deterministic logic)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from log_monitor.lib.dedup_store import DedupStore
from log_monitor.lib.models import LogEntry
from log_monitor.lib.pipeline import run_monitor_tick
from log_monitor.lib.scoring import fingerprint_for, group_and_score


@pytest.fixture
def dedup_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DedupStore:
    path = tmp_path / "seen.json"
    monkeypatch.setattr("log_monitor.lib.pipeline.DedupStore", lambda: DedupStore(path))
    monkeypatch.setattr("log_monitor.lib.dedup_store.DEFAULT_STORE_PATH", path)
    return DedupStore(path)


def test_fingerprint_normalizes_dynamic_values() -> None:
    a = fingerprint_for("svc", "error", "timeout after 12 retries id=abc-123")
    b = fingerprint_for("svc", "error", "timeout after 99 retries id=def-456")
    assert a == b


def test_group_and_score_marks_payment_errors_high() -> None:
    entries = [
        LogEntry(
            timestamp="2026-01-01T00:00:00Z",
            service="payments-api",
            level="error",
            message="HTTP 503 upstream timeout contacting payment-gateway",
        )
    ]
    incidents = group_and_score(entries)
    assert len(incidents) == 1
    assert incidents[0].severity in {"HIGH", "SEVERE"}
    assert incidents[0].service == "payments-api"


def test_run_monitor_tick_returns_routing_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_MONITOR_MUTE_MINUTES", "1")
    with tempfile.TemporaryDirectory() as tmp:
        store_path = Path(tmp) / "seen.json"
        monkeypatch.setattr(
            "log_monitor.lib.pipeline.DedupStore",
            lambda: DedupStore(store_path),
        )
        result = run_monitor_tick()
    assert "incidents_json" in result
    assert "needs_llm_triage" in result
    incidents = json.loads(result["incidents_json"])
    assert isinstance(incidents, list)
    assert result["new_incident_count"] == len(incidents)


def test_dedup_store_mute_window() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = DedupStore(Path(tmp) / "seen.json")
        store.mark_seen("fp1", "HIGH", "alerted")
        assert store.is_muted("fp1", mute_minutes=30) is True
        assert store.is_muted("fp2", mute_minutes=30) is False
