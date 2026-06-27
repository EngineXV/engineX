"""Checkpoint listing and resume routes."""

from __future__ import annotations

import logging
from pathlib import Path

from aiohttp import web

from engine.server.routes import resolve_session
from engine.storage.checkpoint_store import CheckpointStore

logger = logging.getLogger(__name__)


def _agent_storage(session) -> Path:
    return session.runner._storage_path  # noqa: SLF001


def _execution_dir(session, execution_id: str) -> Path:
    return _agent_storage(session) / "sessions" / execution_id


async def handle_list_executions(request: web.Request) -> web.Response:
    session, err = resolve_session(request)
    if err:
        return err
    assert session is not None

    sessions_dir = _agent_storage(session) / "sessions"
    executions: list[dict] = []
    if sessions_dir.is_dir():
        for child in sorted(sessions_dir.iterdir(), reverse=True):
            if not child.is_dir():
                continue
            store = CheckpointStore(child)
            index = await store.load_index()
            executions.append(
                {
                    "execution_id": child.name,
                    "checkpoint_count": index.total_checkpoints if index else 0,
                    "latest_checkpoint_id": index.latest_checkpoint_id if index else None,
                }
            )
    return web.json_response({"executions": executions})


async def handle_list_checkpoints(request: web.Request) -> web.Response:
    session, err = resolve_session(request)
    if err:
        return err
    assert session is not None

    execution_id = request.match_info["execution_id"]
    store = CheckpointStore(_execution_dir(session, execution_id))
    checkpoints = await store.list_checkpoints()
    return web.json_response(
        {
            "execution_id": execution_id,
            "checkpoints": [cp.model_dump() for cp in checkpoints],
        }
    )


async def handle_resume_checkpoint(request: web.Request) -> web.Response:
    session, err = resolve_session(request)
    if err:
        return err
    assert session is not None

    execution_id = request.match_info["execution_id"]
    checkpoint_id = request.match_info["checkpoint_id"]
    runtime = session.runtime
    if runtime is None:
        return web.json_response({"error": "Agent runtime unavailable"}, status=503)
    if session.current_exec_id is not None:
        return web.json_response({"error": "Session is already running"}, status=409)

    store = CheckpointStore(_execution_dir(session, execution_id))
    if not await store.checkpoint_exists(checkpoint_id):
        return web.json_response({"error": "Checkpoint not found"}, status=404)

    entry_points = runtime.get_entry_points()
    if not entry_points:
        return web.json_response({"error": "No entry points available"}, status=400)

    recover_state = {
        "resume_session_id": execution_id,
        "resume_from_checkpoint": checkpoint_id,
    }
    execution = await runtime.trigger(
        entry_points[0].id,
        input_data={},
        session_state=recover_state,
    )
    session.current_exec_id = execution
    session.last_execution_id = execution
    return web.json_response(
        {
            "resumed": True,
            "session_id": session.id,
            "execution_id": execution,
            "checkpoint_id": checkpoint_id,
        }
    )


def register_routes(app: web.Application) -> None:
    app.router.add_get("/api/sessions/{session_id}/executions", handle_list_executions)
    app.router.add_get(
        "/api/sessions/{session_id}/executions/{execution_id}/checkpoints",
        handle_list_checkpoints,
    )
    app.router.add_post(
        "/api/sessions/{session_id}/executions/{execution_id}/checkpoints/{checkpoint_id}/resume",
        handle_resume_checkpoint,
    )
