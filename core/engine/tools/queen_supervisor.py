"""Queen Bee supervisor — lifecycle tools for managing a worker graph in-session."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.runner import AgentRunner

logger = logging.getLogger(__name__)


@dataclass
class QueenSupervisor:
    """Tracks queen ↔ worker state within a supervised session."""

    runner: AgentRunner
    worker_graph_id: str = "worker"
    worker_entry_point: str = "default"
    mode: str = "staging"  # staging | running
    worker_exec_id: str | None = None

    @property
    def runtime(self):
        rt = self.runner._agent_runtime  # noqa: SLF001
        if rt is None:
            raise RuntimeError("Agent runtime is not initialized")
        return rt


def register_queen_tools(runner: AgentRunner, supervisor: QueenSupervisor) -> None:
    """Register queen lifecycle tools on the runner before _setup()."""

    async def start_worker(task: str) -> str:
        """Start the worker agent on the given task description or agreement text."""
        task = (task or "").strip()
        if not task:
            return "Error: task cannot be empty."
        try:
            exec_id = await supervisor.runtime.trigger(
                supervisor.worker_entry_point,
                input_data={},
                graph_id=supervisor.worker_graph_id,
            )
            supervisor.worker_exec_id = exec_id
            supervisor.mode = "running"
            entry = supervisor.runtime.get_entry_points(graph_id=supervisor.worker_graph_id)
            entry_node = entry[0].entry_node if entry else "intake"
            for _ in range(100):
                if await supervisor.runtime.inject_input(
                    entry_node,
                    task,
                    graph_id=supervisor.worker_graph_id,
                    is_client_input=True,
                ):
                    break
                await asyncio.sleep(0.1)
            return (
                f"Started worker on task: {task[:120]}{'…' if len(task) > 120 else ''}. "
                f"Execution id: {exec_id[:12]}. I'll monitor and relay updates."
            )
        except Exception as exc:
            logger.exception("start_worker failed")
            return f"Failed to start worker: {exc}"

    async def get_worker_status() -> str:
        """Return whether the worker graph is running and recent activity."""
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
                return (
                    f"Worker execution in progress "
                    f"(id {(supervisor.worker_exec_id or 'unknown')[:12]}…)."
                )
            supervisor.mode = "staging"
            supervisor.worker_exec_id = None
            return "Worker is idle. Use start_worker(task) to begin agreement analysis."
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
        return "Worker is not waiting for input. Try start_worker first."

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
            if cancelled_any:
                return "Worker execution cancelled."
            return "No active worker execution to stop."
        except Exception as exc:
            return f"Stop worker failed: {exc}"

    for fn in (start_worker, get_worker_status, inject_worker_message, stop_worker):
        runner.register_tool(fn.__name__, fn)

    runner._queen_supervisor = supervisor  # noqa: SLF001


def queen_tool_names() -> list[str]:
    return ["start_worker", "get_worker_status", "inject_worker_message", "stop_worker"]
