"""Tests for supervisor action plans and templates."""

from __future__ import annotations

import pytest

from engine.tasks.models import TaskStatus
from engine.tasks.scoping import supervisor_session_task_list_id
from engine.tasks.store import TaskStore
from engine.tasks.supervisor import parse_task_specs, seed_supervisor_action_plan
from engine.tasks.supervisor_templates import plan_for_department


def test_plan_for_department_legal_has_items() -> None:
    plan = plan_for_department("Legal")
    assert len(plan) >= 3
    assert plan[0]["subject"]


def test_parse_task_specs_newlines() -> None:
    specs = parse_task_specs("First task\nSecond task")
    assert len(specs) == 2
    assert specs[0]["subject"] == "First task"


@pytest.mark.asyncio
async def test_seed_supervisor_action_plan_idempotent(tmp_path) -> None:
    store = TaskStore(engine_root=tmp_path)
    session_id = "dash-001"
    first = await seed_supervisor_action_plan(session_id, department="Technology", store=store)
    second = await seed_supervisor_action_plan(session_id, department="Technology", store=store)
    assert len(first) >= 3
    assert len(second) == len(first)
    assert supervisor_session_task_list_id(session_id).startswith("supervisor:")


@pytest.mark.asyncio
async def test_supervisor_task_status_update(tmp_path) -> None:
    store = TaskStore(engine_root=tmp_path)
    session_id = "dash-002"
    created = await seed_supervisor_action_plan(session_id, store=store)
    task_list_id = supervisor_session_task_list_id(session_id)
    updated = await store.update_task(
        task_list_id,
        created[0].id,
        status=TaskStatus.IN_PROGRESS,
    )
    assert updated is not None
    assert updated.status == TaskStatus.IN_PROGRESS


def test_parse_task_specs_invalid_json_raises() -> None:
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_task_specs("[not json")


def test_session_supervisor_blocks_concurrent_spawn() -> None:
    from engine.tools.supervisor_runtime import SessionSupervisor

    class _Runtime:
        def get_waiting_nodes(self):
            return [{"graph_id": "worker", "node_id": "intake"}]

        def get_active_streams(self):
            return []

    class _Runner:
        _agent_runtime = _Runtime()

    supervisor = SessionSupervisor(runner=_Runner())  # type: ignore[arg-type]
    assert supervisor.is_worker_active() is True
