"""Tests for supervisor worker spawn and plan linkage."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from engine.tasks.models import TaskStatus
from engine.tasks.scoping import supervisor_session_task_list_id
from engine.tasks.store import TaskStore
from engine.tasks.supervisor import seed_supervisor_action_plan
from engine.tools.supervisor_runtime import SessionSupervisor


class _Runtime:
    def __init__(self, *, worker_active: bool = False) -> None:
        self.event_bus = None
        self._worker_active = worker_active
        self.trigger = AsyncMock(return_value="exec-abc123456789")
        self.inject_input = AsyncMock(return_value=True)
        self.get_entry_points = MagicMock(
            return_value=[MagicMock(entry_node="intake")],
        )

    def get_waiting_nodes(self):
        if self._worker_active:
            return [{"graph_id": "worker", "node_id": "intake"}]
        return []

    def get_active_streams(self):
        if self._worker_active:
            return [{"graph_id": "worker", "active_execution_ids": ["exec-1"]}]
        return []


class _Runner:
    def __init__(self, runtime: _Runtime) -> None:
        self._agent_runtime = runtime


@pytest.mark.asyncio
async def test_spawn_worker_links_plan_item(tmp_path) -> None:
    store = TaskStore(engine_root=tmp_path)
    session_id = "spawn-test"
    created = await seed_supervisor_action_plan(session_id, store=store)
    task_id = created[0].id

    runtime = _Runtime()
    supervisor = SessionSupervisor(runner=_Runner(runtime), session_id=session_id)
    supervisor._task_store = store  # noqa: SLF001

    result = await supervisor._spawn_worker_impl("Analyze vendor MSA", task_id=task_id)

    assert "Spawned worker" in result
    assert f"#{task_id}" in result
    runtime.trigger.assert_awaited_once()
    runtime.inject_input.assert_awaited()

    records = await store.list_tasks(supervisor_session_task_list_id(session_id))
    linked = next(r for r in records if r.id == task_id)
    assert linked.status == TaskStatus.IN_PROGRESS
    assert supervisor.active_task_id == task_id


@pytest.mark.asyncio
async def test_on_worker_execution_finished_completes_linked_plan_item(tmp_path) -> None:
    store = TaskStore(engine_root=tmp_path)
    session_id = "finish-test"
    created = await seed_supervisor_action_plan(session_id, store=store)
    task_id = created[0].id
    task_list_id = supervisor_session_task_list_id(session_id)
    await store.update_task(task_list_id, task_id, status=TaskStatus.IN_PROGRESS)

    runtime = _Runtime()
    supervisor = SessionSupervisor(runner=_Runner(runtime), session_id=session_id)
    supervisor._task_store = store  # noqa: SLF001
    supervisor.active_task_id = task_id

    await supervisor.on_worker_execution_finished(success=True)

    records = await store.list_tasks(task_list_id)
    updated = next(r for r in records if r.id == task_id)
    assert updated.status == TaskStatus.COMPLETED
    assert supervisor.active_task_id is None
    assert supervisor.mode == "staging"


@pytest.mark.asyncio
async def test_spawn_worker_rejects_when_worker_already_active(tmp_path) -> None:
    store = TaskStore(engine_root=tmp_path)
    session_id = "busy-test"
    await seed_supervisor_action_plan(session_id, store=store)

    runtime = _Runtime(worker_active=True)
    supervisor = SessionSupervisor(runner=_Runner(runtime), session_id=session_id)
    supervisor._task_store = store  # noqa: SLF001

    result = await supervisor._spawn_worker_impl("Second task")

    assert result.startswith("Error:")
    assert "already active" in result
    runtime.trigger.assert_not_awaited()
