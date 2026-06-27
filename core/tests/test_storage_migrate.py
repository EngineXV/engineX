"""Tests for session state migration helpers."""

from __future__ import annotations

from engine.storage.migrate import migrate_session_state


def test_migrate_preserves_semantic_schema_version() -> None:
    state = {
        "schema_version": "1.1",
        "session_id": "session_20260101_120000_abcd1234",
        "goal_id": "demo",
        "timestamps": {
            "started_at": "2026-01-01T12:00:00",
            "updated_at": "2026-01-01T12:00:00",
        },
        "memory": {"contract_text": "sample"},
    }
    assert migrate_session_state(state) == state


def test_migrate_upgrades_integer_v1_schema() -> None:
    state = {
        "schema_version": 1,
        "paused_at": "review",
        "execution_path": ["intake", "review"],
    }
    migrated = migrate_session_state(state)
    assert migrated["schema_version"] == 2
    assert migrated["progress"]["current_node"] == "review"
    assert migrated["progress"]["path"] == ["intake", "review"]
