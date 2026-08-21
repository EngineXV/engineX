"""Tests for SharedStateManager persistence to the session store.

Simulates a stateless worker restart: two separate SharedStateManager
instances bound to the same session id must share state through the
session store.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from engine.runtime.shared_state import IsolationLevel, SharedStateManager
from engine.schemas.session_state import SessionState, SessionStatus, SessionTimestamps
from engine.storage.session_store import SessionStore

SESSION_ID = "session_test_restart"


def _write_seed_state(store: SessionStore, session_id: str) -> None:
    """Write an initial state.json, mimicking the executor's own write."""
    state = SessionState(
        session_id=session_id,
        goal_id="test-goal",
        stream_id="api",
        status=SessionStatus.ACTIVE,
        timestamps=SessionTimestamps(
            started_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        ),
        memory={"executor_output": "already-persisted"},
    )
    state_path = store.get_state_path(session_id)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")


async def _drain_persist_tasks(manager: SharedStateManager) -> None:
    """Wait for queued persistence snapshots to finish writing."""
    await manager.flush()


@pytest.mark.asyncio
async def test_shared_state_survives_restart(tmp_path: Path):
    """State written by one manager is restored by a new manager (same session)."""
    store = SessionStore(tmp_path)
    _write_seed_state(store, SESSION_ID)

    # --- Worker 1: write shared state ---
    manager_a = SharedStateManager(session_store=store, session_id=SESSION_ID)
    mem_a = manager_a.create_memory(
        execution_id="exec-1",
        stream_id="stream-1",
        isolation=IsolationLevel.SHARED,
    )

    # Global-scope write (across all streams/executions)
    await manager_a.write(
        key="team_key",
        value="team_value",
        execution_id="exec-1",
        stream_id="stream-1",
        isolation=IsolationLevel.SHARED,
        scope="global",
    )
    # Stream-scope write
    await mem_a.write("stream_key", "stream_value", scope="stream")
    # Execution-scope write
    await mem_a.write("exec_key", "exec_value", scope="execution")

    await _drain_persist_tasks(manager_a)

    # Persisted without clobbering the executor's own state.json fields.
    raw = json.loads(store.get_state_path(SESSION_ID).read_text(encoding="utf-8"))
    assert raw["memory"]["executor_output"] == "already-persisted"
    assert raw["shared_state"]["global"]["team_key"] == "team_value"
    assert raw["shared_state"]["streams"]["stream-1"]["stream_key"] == "stream_value"
    assert raw["shared_state"]["executions"]["exec-1"]["exec_key"] == "exec_value"

    # --- Worker 2: a brand-new manager restores the same session ---
    manager_b = SharedStateManager(session_store=store, session_id=SESSION_ID)
    assert manager_b._global_state["team_key"] == "team_value"
    assert manager_b._stream_state["stream-1"]["stream_key"] == "stream_value"
    assert manager_b._execution_state["exec-1"]["exec_key"] == "exec_value"

    # Reads through the public API work from the restored state.
    value = await manager_b.read(
        key="team_key",
        execution_id="exec-9",  # a different execution on a new worker
        stream_id="stream-1",
        isolation=IsolationLevel.SHARED,
    )
    assert value == "team_value"

    value = await manager_b.read(
        key="exec_key",
        execution_id="exec-1",
        stream_id="stream-1",
        isolation=IsolationLevel.SHARED,
    )
    assert value == "exec_value"

    manager_a.close()
    manager_b.close()


@pytest.mark.asyncio
async def test_shared_state_survives_restart_sync_api(tmp_path: Path):
    """write_sync persists; a new manager in the same loop restores it."""
    store = SessionStore(tmp_path)
    _write_seed_state(store, SESSION_ID)

    manager_a = SharedStateManager(session_store=store, session_id=SESSION_ID)
    mem_a = manager_a.create_memory(
        execution_id="exec-sync",
        stream_id="stream-sync",
        isolation=IsolationLevel.SHARED,
    )
    mem_a.write_sync("sync_key", "sync_value")
    await _drain_persist_tasks(manager_a)

    # New manager constructed inside the running loop.
    manager_b = SharedStateManager(session_store=store, session_id=SESSION_ID)
    assert manager_b._execution_state["exec-sync"]["sync_key"] == "sync_value"

    manager_a.close()
    manager_b.close()
