"""REST routes for session task lists."""

from __future__ import annotations

import logging

from aiohttp import web

from engine.tasks import get_task_store, session_task_list_id
from engine.tasks.models import TaskStatus

logger = logging.getLogger(__name__)


def _task_payload(record) -> dict:
    return {
        "id": record.id,
        "subject": record.subject,
        "description": record.description,
        "active_form": record.active_form,
        "owner": record.owner,
        "status": record.status.value,
        "blocks": list(record.blocks),
        "blocked_by": list(record.blocked_by),
        "metadata": dict(record.metadata),
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


async def handle_get_task_list(request: web.Request) -> web.Response:
    raw = request.match_info.get("task_list_id", "")
    if not raw:
        return web.json_response({"error": "task_list_id required"}, status=400)

    store = get_task_store()
    if not await store.list_exists(raw):
        return web.json_response(
            {"error": f"Task list {raw!r} not found", "task_list_id": raw, "tasks": []},
            status=404,
        )

    records = await store.list_tasks(raw)
    return web.json_response(
        {
            "task_list_id": raw,
            "tasks": [_task_payload(r) for r in records],
        }
    )


async def handle_get_session_tasks(request: web.Request) -> web.Response:
    session_id = request.match_info.get("session_id", "")
    if not session_id:
        return web.json_response({"error": "session_id required"}, status=400)

    use_supervisor = request.query.get("supervisor", "").lower() in {"1", "true", "yes"}
    manager = request.app.get("manager")
    if manager is not None and not use_supervisor:
        session = manager.get_session(session_id)
        if session is not None and session.supervised:
            use_supervisor = True

    if use_supervisor:
        from engine.tasks.scoping import supervisor_session_task_list_id

        task_list_id = supervisor_session_task_list_id(session_id)
    else:
        agent_id = request.query.get("agent_id", "default")
        task_list_id = session_task_list_id(agent_id, session_id)

    store = get_task_store()
    exists = await store.list_exists(task_list_id)
    tasks = await store.list_tasks(task_list_id) if exists else []
    return web.json_response(
        {
            "task_list_id": task_list_id if exists else None,
            "tasks": [_task_payload(r) for r in tasks],
        }
    )


async def handle_create_session_tasks(request: web.Request) -> web.Response:
    session_id = request.match_info.get("session_id", "")
    if not session_id:
        return web.json_response({"error": "session_id required"}, status=400)

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    agent_id = str(body.get("agent_id", "default"))
    specs = body.get("tasks", [])
    if not isinstance(specs, list) or not specs:
        return web.json_response({"error": "tasks array required"}, status=400)

    task_list_id = session_task_list_id(agent_id, session_id)
    store = get_task_store()
    await store.ensure_task_list(task_list_id)
    created = await store.create_tasks_batch(task_list_id, specs)
    return web.json_response(
        {"task_list_id": task_list_id, "tasks": [_task_payload(r) for r in created]}
    )


async def handle_patch_task(request: web.Request) -> web.Response:
    task_list_id = request.match_info.get("task_list_id", "")
    task_id = int(request.match_info.get("task_id", "0"))
    if not task_list_id or not task_id:
        return web.json_response({"error": "task_list_id and task_id required"}, status=400)

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    status_raw = body.get("status")
    status = TaskStatus(status_raw) if status_raw else None
    store = get_task_store()
    updated = await store.update_task(
        task_list_id,
        task_id,
        status=status,
        subject=body.get("subject"),
        description=body.get("description"),
    )
    if updated is None:
        return web.json_response({"error": "Task not found"}, status=404)
    return web.json_response({"task": _task_payload(updated)})


def register_routes(app: web.Application) -> None:
    app.router.add_get("/api/tasks/{task_list_id}", handle_get_task_list)
    app.router.add_get("/api/sessions/{session_id}/tasks", handle_get_session_tasks)
    app.router.add_post("/api/sessions/{session_id}/tasks", handle_create_session_tasks)
    app.router.add_patch("/api/tasks/{task_list_id}/{task_id}", handle_patch_task)
