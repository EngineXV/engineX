"""Supervisor lifecycle tools — worker spawn + session action plans."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from engine.tasks.models import TaskStatus
from engine.tasks.scoping import supervisor_session_task_list_id
from engine.tasks.store import get_task_store
from engine.tasks.supervisor import (
    emit_supervisor_tasks_updated,
    format_tasks_for_tool,
    parse_task_specs,
)

if TYPE_CHECKING:
    from engine.runner import AgentRunner

logger = logging.getLogger(__name__)

WORKER_GRAPH_ID = "worker"


@dataclass
class SessionSupervisor:
    """Tracks supervisor ↔ worker state and the session action plan."""

    runner: AgentRunner
    session_id: str = ""
    department: str | None = None
    worker_graph_id: str = WORKER_GRAPH_ID
    worker_entry_point: str = "default"
    mode: str = "staging"  # staging | running
    worker_exec_id: str | None = None
    active_task_id: int | None = None
    _task_store: object = field(default_factory=get_task_store, repr=False)

    @property
    def runtime(self):
        rt = self.runner._agent_runtime  # noqa: SLF001
        if rt is None:
            raise RuntimeError("Agent runtime is not initialized")
        return rt

    @property
    def task_list_id(self) -> str:
        if not self.session_id:
            raise RuntimeError("Supervisor session_id is not set")
        return supervisor_session_task_list_id(self.session_id)

    def is_worker_active(self) -> bool:
        """Return True when the worker graph is running or waiting for input."""
        waiting = self.runtime.get_waiting_nodes()
        if any(w.get("graph_id") == self.worker_graph_id for w in waiting):
            return True
        active = self.runtime.get_active_streams()
        return any(s.get("graph_id") == self.worker_graph_id for s in active)

    async def _refresh_task_event(self) -> None:
        tasks = await self._task_store.list_tasks(self.task_list_id)  # type: ignore[union-attr]
        await emit_supervisor_tasks_updated(
            self.runtime.event_bus,
            session_id=self.session_id,
            tasks=tasks,
        )

    async def on_worker_execution_finished(self, *, success: bool) -> None:
        """Update supervisor state when a worker execution ends."""
        self.mode = "staging"
        self.worker_exec_id = None
        if self.active_task_id is None:
            return
        status = TaskStatus.COMPLETED if success else TaskStatus.PENDING
        await self._task_store.update_task(  # type: ignore[union-attr]
            self.task_list_id,
            self.active_task_id,
            status=status,
        )
        self.active_task_id = None
        await self._refresh_task_event()

    async def _spawn_worker_impl(self, task: str, task_id: int | None = None) -> str:
        task = (task or "").strip()
        if not task:
            return "Error: task cannot be empty."

        if self.is_worker_active():
            return (
                "Error: a worker execution is already active. "
                "Call get_worker_status(), inject_worker_message(), or stop_worker() first."
            )

        if task_id is not None:
            await self._task_store.update_task(  # type: ignore[union-attr]
                self.task_list_id,
                task_id,
                status=TaskStatus.IN_PROGRESS,
            )
            self.active_task_id = task_id
            await self._refresh_task_event()

        session_state = {"session_id": self.session_id} if self.session_id else None
        exec_id = await self.runtime.trigger(
            self.worker_entry_point,
            input_data={},
            graph_id=self.worker_graph_id,
            session_state=session_state,
        )
        self.worker_exec_id = exec_id
        self.mode = "running"

        entry = self.runtime.get_entry_points(graph_id=self.worker_graph_id)
        entry_node = entry[0].entry_node if entry else "intake"
        for _ in range(100):
            if await self.runtime.inject_input(
                entry_node,
                task,
                graph_id=self.worker_graph_id,
                is_client_input=True,
            ):
                break
            await asyncio.sleep(0.1)

        task_note = f" (plan item #{task_id})" if task_id else ""
        exec_short = (exec_id or "unknown")[:12]
        return (
            f"Spawned worker{task_note} with task: {task[:120]}{'…' if len(task) > 120 else ''}. "
            f"Execution id: {exec_short}. Monitoring progress."
        )


def register_supervisor_tools(
    runner: AgentRunner,
    supervisor: SessionSupervisor,
    *,
    session_id: str = "",
    department: str | None = None,
) -> None:
    """Register supervisor lifecycle + action-plan tools on the runner."""
    if session_id:
        supervisor.session_id = session_id
    if department:
        supervisor.department = department

    async def create_action_plan(tasks: str) -> str:
        """Add plan items. Pass newline-separated subjects or a JSON list."""
        try:
            specs = parse_task_specs(tasks)
            if not specs:
                return "Error: provide at least one task subject."
            await supervisor._task_store.ensure_task_list(supervisor.task_list_id)  # type: ignore[union-attr]
            created = await supervisor._task_store.create_tasks_batch(  # type: ignore[union-attr]
                supervisor.task_list_id,
                specs,
            )
            await supervisor._refresh_task_event()
            ids = ", ".join(f"#{r.id}" for r in created)
            return f"Added {len(created)} plan item(s): {ids}."
        except Exception as exc:
            logger.exception("create_action_plan failed")
            return f"Failed to update action plan: {exc}"

    async def list_action_plan() -> str:
        """List the current supervisor action plan with statuses."""
        try:
            records = await supervisor._task_store.list_tasks(supervisor.task_list_id)  # type: ignore[union-attr]
            return format_tasks_for_tool(records)
        except Exception as exc:
            return f"Could not read action plan: {exc}"

    async def update_action_plan_task(task_id: int, status: str) -> str:
        """Update a plan item status: pending, in_progress, or completed."""
        try:
            normalized = status.strip().lower()
            if normalized not in {s.value for s in TaskStatus}:
                return f"Invalid status '{status}'. Use pending, in_progress, or completed."
            updated = await supervisor._task_store.update_task(  # type: ignore[union-attr]
                supervisor.task_list_id,
                int(task_id),
                status=TaskStatus(normalized),
            )
            if updated is None:
                return f"Task #{task_id} not found."
            await supervisor._refresh_task_event()
            return f"Updated task #{task_id} to {normalized}."
        except Exception as exc:
            return f"Failed to update task: {exc}"

    async def spawn_worker(task: str, task_id: int | None = None) -> str:
        """Spawn the worker agent with the given task text. Optionally link to plan item task_id."""
        try:
            return await supervisor._spawn_worker_impl(task, task_id)
        except Exception as exc:
            logger.exception("spawn_worker failed")
            return f"Failed to spawn worker: {exc}"

    async def start_worker(task: str) -> str:
        """Legacy alias for spawn_worker(task)."""
        return await spawn_worker(task)

    async def get_worker_status() -> str:
        """Return whether the worker graph is running and recent activity (read-only)."""
        try:
            waiting = supervisor.runtime.get_waiting_nodes()
            worker_waiting = [w for w in waiting if w.get("graph_id") == supervisor.worker_graph_id]
            if worker_waiting:
                node = worker_waiting[0]
                return (
                    f"Worker waiting for input at node '{node.get('node_id', '?')}'. "
                    "The operator may need to reply in the dashboard."
                )
            active = supervisor.runtime.get_active_streams()
            worker_active = [s for s in active if s.get("graph_id") == supervisor.worker_graph_id]
            if worker_active:
                supervisor.mode = "running"
                ids = worker_active[0].get("active_execution_ids", [])
                if ids:
                    supervisor.worker_exec_id = ids[0]
                plan = ""
                if supervisor.active_task_id is not None:
                    plan = f" Linked plan item #{supervisor.active_task_id}."
                worker_id = supervisor.worker_exec_id or "unknown"
                return f"Worker execution in progress (id {worker_id[:12]}…).{plan}"
            supervisor.mode = "staging"
            supervisor.worker_exec_id = None
            if supervisor.active_task_id is not None:
                return (
                    "Worker is idle with plan item "
                    f"#{supervisor.active_task_id} still in progress. "
                    "It will update when the worker execution completes."
                )
            return "Worker is idle. Use spawn_worker(task) or list_action_plan()."
        except Exception as exc:
            return f"Could not read worker status: {exc}"

    async def inject_worker_message(message: str) -> str:
        """Send a message into the running worker (e.g. agreement text or approval)."""
        message = (message or "").strip()
        if not message:
            return "Error: message cannot be empty."
        waiting = supervisor.runtime.get_waiting_nodes()
        for w in waiting:
            if w.get("graph_id") == supervisor.worker_graph_id:
                node_id = w.get("node_id")
                if node_id and await supervisor.runtime.inject_input(
                    node_id,
                    message,
                    graph_id=supervisor.worker_graph_id,
                    is_client_input=True,
                ):
                    return f"Delivered message to worker node '{node_id}'."
        entry = supervisor.runtime.get_entry_points(graph_id=supervisor.worker_graph_id)
        if entry:
            node_id = entry[0].entry_node
            if await supervisor.runtime.inject_input(
                node_id,
                message,
                graph_id=supervisor.worker_graph_id,
                is_client_input=True,
            ):
                return f"Delivered message to worker entry node '{node_id}'."
        return "Worker is not waiting for input. Try spawn_worker first."

    async def stop_worker() -> str:
        """Cancel the active worker execution if any."""
        try:
            reg = supervisor.runtime.get_graph_registration(supervisor.worker_graph_id)
            if reg is None:
                return "Worker graph is not loaded."
            cancelled_any = False
            for ep_id, stream in reg.streams.items():
                for eid in list(stream.active_execution_ids):
                    await supervisor.runtime.cancel_execution(
                        ep_id,
                        eid,
                        graph_id=supervisor.worker_graph_id,
                    )
                    cancelled_any = True
            supervisor.worker_exec_id = None
            supervisor.mode = "staging"
            if supervisor.active_task_id is not None:
                await supervisor._task_store.update_task(  # type: ignore[union-attr]
                    supervisor.task_list_id,
                    supervisor.active_task_id,
                    status=TaskStatus.PENDING,
                )
                supervisor.active_task_id = None
                await supervisor._refresh_task_event()
            if cancelled_any:
                return "Worker execution cancelled."
            return "No active worker execution to stop."
        except Exception as exc:
            return f"Stop worker failed: {exc}"

    for fn in (
        create_action_plan,
        list_action_plan,
        update_action_plan_task,
        spawn_worker,
        start_worker,
        get_worker_status,
        inject_worker_message,
        stop_worker,
    ):
        runner.register_tool(fn.__name__, fn)

    runner._session_supervisor = supervisor  # noqa: SLF001


def supervisor_tool_names() -> list[str]:
    return [
        "create_action_plan",
        "list_action_plan",
        "update_action_plan_task",
        "spawn_worker",
        "start_worker",
        "get_worker_status",
        "inject_worker_message",
        "stop_worker",
    ]
