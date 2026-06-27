"""Tests for session task store."""

from __future__ import annotations

import pytest

from engine.tasks.models import TaskStatus
from engine.tasks.scoping import session_task_list_id
from engine.tasks.store import TaskStore


@pytest.mark.asyncio
async def test_task_store_create_and_list(tmp_path) -> None:
    store = TaskStore(engine_root=tmp_path)
    task_list_id = session_task_list_id("demo", "session_1")
    created = await store.create_tasks_batch(
        task_list_id,
        [{"subject": "Review logs"}, {"subject": "Send alert"}],
    )
    assert len(created) == 2
    tasks = await store.list_tasks(task_list_id)
    assert [t.subject for t in tasks] == ["Review logs", "Send alert"]


@pytest.mark.asyncio
async def test_task_store_update_status(tmp_path) -> None:
    store = TaskStore(engine_root=tmp_path)
    task_list_id = session_task_list_id("demo", "session_2")
    created = await store.create_tasks_batch(task_list_id, [{"subject": "Ship feature"}])
    updated = await store.update_task(
        task_list_id,
        created[0].id,
        status=TaskStatus.COMPLETED,
    )
    assert updated is not None
    assert updated.status == TaskStatus.COMPLETED
