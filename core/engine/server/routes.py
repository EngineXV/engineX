"""HTTP routes for the Engine dashboard API."""

from __future__ import annotations

import asyncio
import json
import logging

from aiohttp import web
from aiohttp.client_exceptions import ClientConnectionResetError as _AiohttpConnReset

from engine.config import get_preferred_model
from engine.credentials.models import CredentialError
from engine.runtime.event_bus import EventType
from engine.runtime.execution_stream import ExecutionAlreadyRunningError
from engine.server.discovery import discover_agents, resolve_agent_path
from engine.server.session import Session, SessionManager
from engine.server.sse import SSEResponse

logger = logging.getLogger(__name__)

KEEPALIVE_INTERVAL = 15.0

DEFAULT_EVENT_TYPES = [
    EventType.CLIENT_OUTPUT_DELTA,
    EventType.CLIENT_INPUT_REQUESTED,
    EventType.LLM_TEXT_DELTA,
    EventType.TOOL_CALL_STARTED,
    EventType.TOOL_CALL_COMPLETED,
    EventType.EXECUTION_STARTED,
    EventType.EXECUTION_COMPLETED,
    EventType.EXECUTION_FAILED,
    EventType.EXECUTION_PAUSED,
    EventType.NODE_LOOP_STARTED,
    EventType.NODE_LOOP_ITERATION,
    EventType.NODE_LOOP_COMPLETED,
    EventType.LLM_TURN_COMPLETE,
    EventType.NODE_ACTION_PLAN,
    EventType.GOAL_PROGRESS,
    EventType.GOAL_ACHIEVED,
    EventType.NODE_INTERNAL_OUTPUT,
    EventType.OUTPUT_KEY_SET,
    EventType.EDGE_TRAVERSED,
]


def _manager(request: web.Request) -> SessionManager:
    return request.app["manager"]


def _repo_root(request: web.Request):
    return request.app["repo_root"]


def resolve_session(request: web.Request) -> tuple[Session | None, web.Response | None]:
    session_id = request.match_info.get("session_id", "")
    session = _manager(request).get_session(session_id)
    if session is None:
        return None, web.json_response({"error": "Session not found"}, status=404)
    return session, None


def _credential_error_response(exc: CredentialError, agent_path: str) -> web.Response:
    return web.json_response(
        {
            "error": "credentials_required",
            "message": str(exc),
            "agent_path": agent_path,
        },
        status=424,
    )


async def handle_health(_request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def handle_config(_request: web.Request) -> web.Response:
    from engine.llm.model_catalog import get_default_models, get_models_catalogue, get_presets

    return web.json_response(
        {
            "model": get_preferred_model(),
            "catalog": get_models_catalogue(),
            "defaults": get_default_models(),
            "presets": get_presets(),
        }
    )


async def handle_discover(request: web.Request) -> web.Response:
    manager = _manager(request)
    loaded_paths = {str(s.agent_path) for s in manager.list_sessions()}
    groups = discover_agents(_repo_root(request), loaded_paths)
    return web.json_response(groups)


async def handle_create_session(request: web.Request) -> web.Response:
    manager = _manager(request)
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON body"}, status=400)
    if not isinstance(body, dict):
        return web.json_response({"error": "Request body must be a JSON object"}, status=400)

    agent_path_raw = body.get("agent_path")
    if not agent_path_raw:
        return web.json_response({"error": "agent_path is required"}, status=400)

    resolved = resolve_agent_path(_repo_root(request), agent_path_raw)
    if resolved is None:
        return web.json_response({"error": f"Agent not found: {agent_path_raw}"}, status=404)

    session_id = body.get("session_id")
    model = body.get("model")

    try:
        session = await manager.create_session(
            resolved,
            session_id=session_id,
            model=model,
        )
    except CredentialError as exc:
        return _credential_error_response(exc, str(resolved))
    except ValueError as exc:
        return web.json_response({"error": str(exc)}, status=409)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to create session")
        return web.json_response({"error": str(exc)}, status=500)

    return web.json_response(session.to_dict(), status=201)


async def handle_list_sessions(request: web.Request) -> web.Response:
    sessions = _manager(request).list_sessions()
    return web.json_response({"sessions": [s.to_dict() for s in sessions]})


async def handle_get_session(request: web.Request) -> web.Response:
    session, err = resolve_session(request)
    if err:
        return err
    assert session is not None
    return web.json_response(session.detail_dict())


async def handle_delete_session(request: web.Request) -> web.Response:
    session_id = request.match_info["session_id"]
    stopped = await _manager(request).delete_session(session_id)
    if not stopped:
        return web.json_response({"error": "Session not found"}, status=404)
    return web.json_response({"session_id": session_id, "stopped": True})


async def handle_message(request: web.Request) -> web.Response:
    session, err = resolve_session(request)
    if err:
        return err
    assert session is not None

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    message = body.get("message", "")
    try:
        result = await _manager(request).send_message(session, message)
    except ExecutionAlreadyRunningError as exc:
        return web.json_response({"error": str(exc)}, status=409)
    except ValueError as exc:
        return web.json_response({"error": str(exc)}, status=400)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Message delivery failed")
        return web.json_response({"error": str(exc)}, status=500)

    return web.json_response(result)


async def handle_pause_session(request: web.Request) -> web.Response:
    session, err = resolve_session(request)
    if err:
        return err
    assert session is not None
    try:
        result = await _manager(request).pause_session(session)
    except Exception as exc:  # noqa: BLE001
        return web.json_response({"error": str(exc)}, status=500)
    return web.json_response(result)


async def handle_resume_session(request: web.Request) -> web.Response:
    session, err = resolve_session(request)
    if err:
        return err
    assert session is not None
    try:
        result = await _manager(request).resume_session(session)
    except ExecutionAlreadyRunningError as exc:
        return web.json_response({"error": str(exc)}, status=409)
    except Exception as exc:  # noqa: BLE001
        return web.json_response({"error": str(exc)}, status=500)
    return web.json_response(result)


async def handle_metrics(_request: web.Request) -> web.Response:
    from engine.observability.metrics import prometheus_text

    return web.Response(text=prometheus_text(), content_type="text/plain; version=0.0.4")


def _parse_event_types(query_param: str | None) -> list[EventType]:
    if not query_param:
        return DEFAULT_EVENT_TYPES
    result = []
    for name in query_param.split(","):
        name = name.strip()
        try:
            result.append(EventType(name))
        except ValueError:
            logger.warning("Unknown event type filter: %s", name)
    return result or DEFAULT_EVENT_TYPES


async def handle_events(request: web.Request) -> web.StreamResponse:
    session, err = resolve_session(request)
    if err:
        return err
    assert session is not None

    event_bus = session.event_bus
    if event_bus is None:
        return web.json_response({"error": "Event bus unavailable"}, status=503)

    event_types = _parse_event_types(request.query.get("types"))
    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
    client_disconnected = asyncio.Event()
    close_reason = "unknown"
    event_count = 0

    async def on_event(event) -> None:
        if client_disconnected.is_set():
            return
        try:
            queue.put_nowait(event.to_dict())
        except asyncio.QueueFull:
            client_disconnected.set()

    sub_id = event_bus.subscribe(event_types=event_types, handler=on_event)

    sse = SSEResponse()
    await sse.prepare(request)

    try:
        while not client_disconnected.is_set():
            try:
                evt_dict = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_INTERVAL)
                await sse.send_event(evt_dict)
                event_count += 1
            except TimeoutError:
                try:
                    await sse.send_keepalive()
                except (ConnectionResetError, ConnectionError, _AiohttpConnReset):
                    close_reason = "client_disconnected"
                    break
            except (ConnectionResetError, ConnectionError, _AiohttpConnReset):
                close_reason = "client_disconnected"
                break
            except RuntimeError as exc:
                if "closing transport" in str(exc).lower():
                    close_reason = "client_disconnected"
                else:
                    close_reason = f"error: {exc}"
                break
    except asyncio.CancelledError:
        close_reason = "cancelled"
    finally:
        event_bus.unsubscribe(sub_id)
        logger.info(
            "SSE disconnected: session='%s', events_sent=%d, reason='%s'",
            session.id,
            event_count,
            close_reason,
        )

    return sse.response  # type: ignore[return-value]


def register_routes(app: web.Application) -> None:
    app.router.add_get("/api/health", handle_health)
    app.router.add_get("/api/config", handle_config)
    app.router.add_get("/api/discover", handle_discover)
    app.router.add_post("/api/sessions", handle_create_session)
    app.router.add_get("/api/sessions", handle_list_sessions)
    app.router.add_get("/api/sessions/{session_id}", handle_get_session)
    app.router.add_delete("/api/sessions/{session_id}", handle_delete_session)
    app.router.add_post("/api/sessions/{session_id}/message", handle_message)
    app.router.add_post("/api/sessions/{session_id}/pause", handle_pause_session)
    app.router.add_post("/api/sessions/{session_id}/resume", handle_resume_session)
    app.router.add_get("/api/sessions/{session_id}/events", handle_events)
    app.router.add_get("/api/metrics", handle_metrics)
