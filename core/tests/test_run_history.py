"""Tests for ops run history collection."""

from __future__ import annotations

import json
from pathlib import Path

from engine.observability import run_history


def test_collect_run_history_includes_cost_and_token_totals(tmp_path, monkeypatch):
    home = tmp_path / "home"
    session_dir = (
        home
        / ".engine"
        / "agents"
        / "agent-a"
        / "sessions"
        / "session_20250101_000000_abcd1234"
    )
    logs_dir = session_dir / "logs"
    logs_dir.mkdir(parents=True)

    (logs_dir / "summary.json").write_text(
        json.dumps(
            {
                "success": True,
                "started_at": "2025-01-01T00:00:00",
                "ended_at": "2025-01-01T00:05:00",
                "total_tokens": 1500,
                "total_input_tokens": 900,
                "total_output_tokens": 600,
                "estimated_cost_usd": 0.42,
            }
        ),
        encoding="utf-8",
    )
    (session_dir / "state.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "metrics": {
                    "total_tokens": 1400,
                    "total_input_tokens": 800,
                    "total_output_tokens": 600,
                    "estimated_cost_usd": 0.38,
                },
                "progress": {"total_tokens": 1400},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(run_history.Path, "home", lambda: home)

    rows = run_history.collect_run_history(Path("."), limit=10)

    assert len(rows) == 1
    row = rows[0]
    assert row["agent"] == "agent-a"
    assert row["total_tokens"] == 1500
    assert row["total_input_tokens"] == 900
    assert row["total_output_tokens"] == 600
    assert row["estimated_cost_usd"] == 0.42