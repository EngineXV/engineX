"""Thin session wrapper around AgentRunner + AgentRuntime."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.credentials.models import CredentialError
from engine.runner import AgentRunner
from engine.runtime.event_bus import AgentEvent, EventBus, EventType
from engine.runtime.execution_stream import ExecutionAlreadyRunningError

logger = logging.getLogger(__name__)

WORKER_GRAPH_ID = "worker"


def _primary_graph_id(session: Session) -> str:
    runtime = session.runtime
    if runtime is not None:
        return runtime._graph_id  # noqa: SLF001
    return "primary"


def _event_graph_id(event: AgentEvent) -> str | None:
    return event.graph_id


def _is_worker_event(session: Session, event: AgentEvent) -> bool:
    return session.supervised and _event_graph_id(event) == WORKER_GRAPH_ID


def _is_primary_event(session: Session, event: AgentEvent) -> bool:
    graph_id = _event_graph_id(event)
    if graph_id is None:
        return True
    return graph_id == _primary_graph_id(session)


@dataclass
class Session:
    id: str
    agent_path: Path
    runner: AgentRunner
    model: str | None
    loaded_at: float = field(default_factory=time.time)
    current_exec_id: str | None = None
    active_node_id: str | None = None
    waiting_for_input: bool = False
    input_node_id: str | None = None
    input_graph_id: str | None = None
    supervised: bool = False
    supervisor_mode: str = "staging"
    _subscription_id: str | None = None

    @property
    def runtime(self):
        return self.runner._agent_runtime

    @property
    def event_bus(self) -> EventBus | None:
        runtime = self.runtime
        return runtime.event_bus if runtime is not None else None

    def to_dict(self) -> dict[str, Any]:
        info = self.runner.info()
        payload = {
            "session_id": self.id,
            "agent_path": str(self.agent_path),
            "name": info.name,
            "description": info.description,
            "goal": info.goal_name,
            "node_count": info.node_count,
            "loaded_at": self.loaded_at,
            "uptime_seconds": round(time.time() - self.loaded_at, 1),
            "intro_message": getattr(self.runtime, "intro_message", "") or "",
            "waiting_for_input": self.waiting_for_input,
            "current_exec_id": self.current_exec_id,
            "supervised": self.supervised,
            "supervisor_mode": self.supervisor_mode,
            "input_graph_id": self.input_graph_id,
        }
        if info.supervisor:
            payload["supervisor"] = True
            payload["supervisor_name"] = info.supervisor_name
            payload["department"] = info.department
            payload["role_title"] = info.role_title
        return payload

    def detail_dict(self) -> dict[str, Any]:
        info = self.runner.info()
        entry_points = []
        if self.runtime is not None:
            entry_points = [
                {
                    "id": ep.id,
                    "name": ep.name,
                    "entry_node": ep.entry_node,
                    "trigger_type": ep.trigger_type,
                }
                for ep in self.runtime.get_entry_points()
            ]
        detail = {
            **self.to_dict(),
            "nodes": info.nodes if hasattr(info, "nodes") else [],
            "edges": info.edges if hasattr(info, "edges") else [],
            "entry_points": entry_points,
            "waiting_nodes": self.runtime.get_waiting_nodes() if self.runtime else [],
        }
        if self.supervised and self.runtime is not None:
            reg = self.runtime.get_graph_registration("worker")
            if reg is not None:
                detail["worker_nodes"] = [
                    {
                        "id": n.id,
                        "name": n.name,
                        "description": n.description,
                        "type": n.node_type,
                    }
                    for n in reg.graph.nodes
                ]
                detail["worker_edges"] = [
                    {
                        "id": e.id,
                        "source": e.source,
                        "target": e.target,
                        "condition": e.condition.value,
                    }
                    for e in reg.graph.edges
                ]
        return detail

    def attach_event_tracking(self) -> None:
        bus = self.event_bus
        if bus is None or self._subscription_id is not None:
            return

        async def on_event(event: AgentEvent) -> None:
            et = event.type

            if _is_worker_event(self, event):
                if et == EventType.EXECUTION_COMPLETED:
                    supervisor = getattr(self.runner, "_session_supervisor", None)
                    if supervisor is not None:
                        await supervisor.on_worker_execution_finished(success=True)
                elif et == EventType.EXECUTION_FAILED:
                    supervisor = getattr(self.runner, "_session_supervisor", None)
                    if supervisor is not None:
                        await supervisor.on_worker_execution_finished(success=False)
                if et == EventType.CLIENT_INPUT_REQUESTED:
                    self.waiting_for_input = True
                    self.input_node_id = event.node_id
                    self.input_graph_id = event.graph_id
                return

            if not _is_primary_event(self, event):
                return

            if et == EventType.EXECUTION_STARTED:
                self.current_exec_id = event.execution_id
                if event.node_id:
                    self.active_node_id = event.node_id
            elif et in (EventType.EXECUTION_COMPLETED, EventType.EXECUTION_FAILED):
                self.current_exec_id = None
                self.active_node_id = None
                self.waiting_for_input = False
                self.input_node_id = None
                self.input_graph_id = None
            elif et == EventType.CLIENT_INPUT_REQUESTED:
                self.waiting_for_input = True
                self.input_node_id = event.node_id
                self.input_graph_id = event.graph_id
            elif et == EventType.NODE_LOOP_STARTED and event.node_id:
                self.active_node_id = event.node_id

        self._subscription_id = bus.subscribe(
            event_types=list(EventType),
            handler=on_event,
        )

    def detach_event_tracking(self) -> None:
        bus = self.event_bus
        if bus is not None and self._subscription_id is not None:
            bus.unsubscribe(self._subscription_id)
            self._subscription_id = None


class SessionManager:
    def __init__(self, repo_root: Path, default_model: str | None = None) -> None:
        self.repo_root = repo_root
        self.default_model = default_model
        self._sessions: dict[str, Session] = {}

    def list_sessions(self) -> list[Session]:
        return list(self._sessions.values())

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    async def create_session(
        self,
        agent_path: Path,
        *,
        session_id: str | None = None,
        model: str | None = None,
    ) -> Session:
        sid = session_id or uuid.uuid4().hex[:12]
        if sid in self._sessions:
            raise ValueError(f"Session already exists: {sid}")

        resolved_model = model or self.default_model
        loop = asyncio.get_running_loop()

        def _load() -> AgentRunner:
            from engine.runtime.event_bus import EventBus

            bus = EventBus()
            runner = AgentRunner.load(
                agent_path,
                model=resolved_model,
                interactive=False,
            )
            if runner.supervised_worker_path is not None:
                from engine.tools.supervisor_runtime import SessionSupervisor

                runner._session_supervisor = SessionSupervisor(runner=runner)  # noqa: SLF001
            if runner._agent_runtime is None:
                runner._setup(event_bus=bus)
            return runner

        try:
            runner = await loop.run_in_executor(None, _load)
        except CredentialError:
            raise

        session = Session(
            id=sid,
            agent_path=agent_path.resolve(),
            runner=runner,
            model=resolved_model,
            supervised=runner.supervised_worker_path is not None,
        )

        runtime = session.runtime
        if runtime is not None and not runtime.is_running:
            await runtime.start()

        if runner.supervised_worker_path is not None:
            info = runner.info()
            supervisor = getattr(runner, "_session_supervisor", None)
            if supervisor is not None:
                from engine.tools.supervisor_runtime import (
                    SessionSupervisor,
                    register_supervisor_tools,
                )

                if not isinstance(supervisor, SessionSupervisor):
                    supervisor = SessionSupervisor(runner=runner)
                register_supervisor_tools(
                    runner,
                    supervisor,
                    session_id=sid,
                    department=getattr(info, "department", None) or None,
                )

            from engine.tasks.supervisor import (
                emit_supervisor_tasks_updated,
                seed_supervisor_action_plan,
            )

            seeded = await seed_supervisor_action_plan(
                sid,
                department=getattr(info, "department", None) or None,
            )
            await emit_supervisor_tasks_updated(
                runtime.event_bus if runtime else None,
                session_id=sid,
                tasks=seeded,
            )

            worker_path = runner.supervised_worker_path
            if not worker_path.is_dir():
                worker_path = (agent_path.parent / worker_path.name).resolve()
            await AgentRunner.setup_as_secondary(worker_path, runtime, graph_id="worker")
            try:
                session.current_exec_id = await runtime.trigger("default", input_data={})
            except Exception as exc:  # noqa: BLE001
                logger.warning("Supervisor auto-start failed for session %s: %s", sid, exc)

        session.attach_event_tracking()
        self._sessions[sid] = session
        return session

    async def delete_session(self, session_id: str) -> bool:
        session = self._sessions.pop(session_id, None)
        if session is None:
            return False
        session.detach_event_tracking()
        try:
            await session.runner.cleanup_async()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Session cleanup failed for %s: %s", session_id, exc)
        return True

    async def shutdown_all(self) -> None:
        for session_id in list(self._sessions):
            await self.delete_session(session_id)

    async def send_message(self, session: Session, message: str) -> dict[str, Any]:
        runtime = session.runtime
        if runtime is None:
            raise RuntimeError("Agent runtime is not available")

        text = message.strip()
        if not text:
            raise ValueError("Message cannot be empty")

        if session.waiting_for_input and session.input_node_id:
            node_id = session.input_node_id
            graph_id = session.input_graph_id
            session.waiting_for_input = False
            session.input_node_id = None
            session.input_graph_id = None
            delivered = await runtime.inject_input(
                node_id, text, graph_id=graph_id, is_client_input=True
            )
            return {"action": "inject", "delivered": delivered, "node_id": node_id}

        if session.current_exec_id is not None and session.active_node_id:
            graph_id = session.input_graph_id
            if graph_id is None and session.supervised and runtime is not None:
                graph_id = runtime._graph_id
            delivered = await runtime.inject_input(
                session.active_node_id,
                text,
                graph_id=graph_id,
                is_client_input=True,
            )
            return {
                "action": "inject",
                "delivered": delivered,
                "node_id": session.active_node_id,
            }

        if session.current_exec_id is not None:
            raise ExecutionAlreadyRunningError("Agent is still running")

        entry_points = runtime.get_entry_points()
        manual_eps = [ep for ep in entry_points if ep.trigger_type in ("manual", "api")]
        if not manual_eps:
            manual_eps = entry_points
        if not manual_eps:
            raise RuntimeError("No entry points available")

        entry_point = manual_eps[0]
        active_graph = runtime.get_active_graph()
        entry_node = active_graph.get_node(entry_point.entry_node)

        # Client-facing entry nodes (e.g. intake) should receive the user's
        # message via inject_input, not as a prefilled output key. Mapping
        # "hi" → contract_text makes weak local models loop on set_output JSON.
        if entry_node and entry_node.client_facing and entry_node.input_keys:
            try:
                execution_id = await runtime.trigger(
                    entry_point_id=entry_point.id,
                    input_data={},
                )
            except ExecutionAlreadyRunningError:
                raise

            session.current_exec_id = execution_id
            for _ in range(100):
                if await runtime.inject_input(
                    entry_point.entry_node,
                    text,
                    is_client_input=True,
                ):
                    return {
                        "action": "trigger",
                        "execution_id": execution_id,
                        "entry_point_id": entry_point.id,
                        "injected": True,
                    }
                await asyncio.sleep(0.1)

            return {
                "action": "trigger",
                "execution_id": execution_id,
                "entry_point_id": entry_point.id,
                "injected": False,
            }

        input_key = entry_node.input_keys[0] if entry_node and entry_node.input_keys else "input"

        try:
            execution_id = await runtime.trigger(
                entry_point_id=entry_point.id,
                input_data={input_key: text},
            )
        except ExecutionAlreadyRunningError:
            raise

        session.current_exec_id = execution_id
        return {
            "action": "trigger",
            "execution_id": execution_id,
            "entry_point_id": entry_point.id,
        }
