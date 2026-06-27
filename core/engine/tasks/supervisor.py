"""Supervisor session action-plan helpers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from engine.tasks.models import TaskListRole, TaskRecord, TaskStatus
from engine.tasks.scoping import supervisor_session_task_list_id
from engine.tasks.store import TaskStore, get_task_store
from engine.tasks.supervisor_templates import plan_for_department

if TYPE_CHECKING:
    from engine.runtime.event_bus import EventBus

logger = logging.getLogger(__name__)


async def seed_supervisor_action_plan(
    session_id: str,
    *,
    department: str | None = None,
    store: TaskStore | None = None,
) -> list[TaskRecord]:
    """Create the default department action plan for a new supervisor session."""
    task_store = store or get_task_store()
    task_list_id = supervisor_session_task_list_id(session_id)
    if await task_store.list_exists(task_list_id):
        return await task_store.list_tasks(task_list_id)

    await task_store.ensure_task_list(task_list_id, role=TaskListRole.SESSION)
    specs = plan_for_department(department)
    return await task_store.create_tasks_batch(task_list_id, specs)


async def emit_supervisor_tasks_updated(
    event_bus: EventBus | None,
    *,
    session_id: str,
    tasks: list[TaskRecord],
    node_id: str = "supervisor",
) -> None:
    """Notify dashboard clients that the supervisor action plan changed."""
    if event_bus is None:
        return
    summary = "\n".join(
        f"- [{'x' if t.status == TaskStatus.COMPLETED else ' '}] #{t.id} {t.subject}" for t in tasks
    )
    try:
        await event_bus.emit_node_action_plan(
            stream_id=session_id,
            node_id=node_id,
            plan=summary or "(empty plan)",
        )
    except Exception:
        logger.debug("Failed to emit supervisor task update", exc_info=True)


def format_tasks_for_tool(tasks: list[TaskRecord]) -> str:
    if not tasks:
        return "No tasks in the action plan yet."
    lines = []
    for task in tasks:
        lines.append(
            f"#{task.id} [{task.status.value}] {task.subject}"
            + (f" — {task.description}" if task.description else "")
        )
    return "\n".join(lines)


def parse_task_specs(raw: str | list[Any]) -> list[dict[str, Any]]:
    """Accept JSON list or newline-separated subjects from the supervisor."""
    if isinstance(raw, list):
        specs: list[dict[str, Any]] = []
        for item in raw:
            if isinstance(item, str) and item.strip():
                specs.append({"subject": item.strip()})
            elif isinstance(item, dict) and item.get("subject"):
                specs.append(dict(item))
        return specs

    text = (raw or "").strip()
    if not text:
        return []
    if text.startswith("["):
        import json

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON task list: {exc}") from exc
        return parse_task_specs(parsed)

    return [{"subject": line.strip()} for line in text.splitlines() if line.strip()]
