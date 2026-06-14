"""Agent Runtime - Top-level orchestrator for multi-entry-point agents"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from engine.graph.checkpoint_config import CheckpointConfig
from engine.graph.executor import ExecutionResult
from engine.runtime.event_bus import EventBus
from engine.runtime.execution_stream import EntryPointSpec, ExecutionStream
from engine.runtime.outcome_aggregator import OutcomeAggregator
from engine.runtime.runtime_log_store import RuntimeLogStore
from engine.runtime.shared_state import SharedStateManager
from engine.storage.concurrent import ConcurrentStorage
from engine.storage.session_store import SessionStore

if TYPE_CHECKING:
    from engine.graph.edge import GraphSpec
    from engine.graph.goal import Goal
    from engine.llm.provider import LLMProvider, Tool

logger = logging.getLogger(__name__)


@dataclass
class AgentRuntimeConfig:
    """Configuration for AgentRuntime"""

    max_concurrent_executions: int = 100
    cache_ttl: float = 60.0
    batch_interval: float = 0.1
    max_history: int = 1000
    execution_result_max: int = 1000
    execution_result_ttl_seconds: float | None = None


@dataclass
class _GraphRegistration:
    """Tracks a loaded graph and its runtime resources"""

    graph: "GraphSpec"
    goal: "Goal"
    entry_points: dict[str, EntryPointSpec]
    streams: dict[str, ExecutionStream]  # ep_id -> stream (NOT namespaced)
    storage_subpath: str  # relative to session root, e.g. "graphs/email_agent"
    event_subscriptions: list[str] = field(default_factory=list)
    timer_tasks: list[asyncio.Task] = field(default_factory=list)
    timer_next_fire: dict[str, float] = field(default_factory=dict)


class AgentRuntime:
    """Top-level runtime that manages agent lifecycle and concurrent"""

    def __init__(
        self,
        graph: "GraphSpec",
        goal: "Goal",
        storage_path: str | Path,
        llm: "LLMProvider | None" = None,
        tools: list["Tool"] | None = None,
        tool_executor: Callable | None = None,
        config: AgentRuntimeConfig | None = None,
        runtime_log_store: Any = None,
        checkpoint_config: CheckpointConfig | None = None,
        graph_id: str | None = None,
        accounts_prompt: str = "",
        accounts_data: list[dict] | None = None,
        tool_provider_map: dict[str, str] | None = None,
        event_bus: "EventBus | None" = None,
    ):
        """Initialize agent runtime"""
        self.graph = graph
        self.goal = goal
        self._config = config or AgentRuntimeConfig()
        self._runtime_log_store = runtime_log_store
        self._checkpoint_config = checkpoint_config
        self.accounts_prompt = accounts_prompt

        # Primary graph identity
        self._graph_id: str = graph_id or "primary"

        # Multi-graph state
        self._graphs: dict[str, _GraphRegistration] = {}
        self._active_graph_id: str = self._graph_id

        # User presence tracking (monotonic timestamp of last inject_input)
        self._last_user_input_time: float = 0.0

        # Initialize storage
        storage_path_obj = Path(storage_path) if isinstance(storage_path, str) else storage_path
        self._storage = ConcurrentStorage(
            base_path=storage_path_obj,
            cache_ttl=self._config.cache_ttl,
            batch_interval=self._config.batch_interval,
        )

        # Initialize SessionStore for unified sessions (always enabled)
        self._session_store = SessionStore(storage_path_obj)

        # Initialize shared components
        self._state_manager = SharedStateManager()
        self._event_bus = event_bus or EventBus(max_history=self._config.max_history)
        self._outcome_aggregator = OutcomeAggregator(goal, self._event_bus)

        # LLM and tools
        self._llm = llm
        self._tools = tools or []
        self._tool_executor = tool_executor
        self._accounts_prompt = accounts_prompt
        self._accounts_data = accounts_data
        self._tool_provider_map = tool_provider_map

        # Entry points and streams (primary graph)
        self._entry_points: dict[str, EntryPointSpec] = {}
        self._streams: dict[str, ExecutionStream] = {}

        # Event-driven entry point subscriptions (primary graph)
        self._event_subscriptions: list[str] = []
        # Timer tasks for scheduled entry points (primary graph)
        self._timer_tasks: list[asyncio.Task] = []
        # Next fire time for each timer entry point (ep_id -> datetime)
        self._timer_next_fire: dict[str, float] = {}

        # State
        self._running = False
        self._timers_paused = False
        self._lock = asyncio.Lock()

        # Optional greeting shown to user on TUI load (set by AgentRunner)
        self.intro_message: str = ""

    def register_entry_point(self, spec: EntryPointSpec) -> None:
        """Register a named entry point for the agent"""
        if self._running:
            raise RuntimeError("Cannot register entry points while runtime is running")

        if spec.id in self._entry_points:
            raise ValueError(f"Entry point '{spec.id}' already registered")

        # Validate entry node exists in graph
        if self.graph.get_node(spec.entry_node) is None:
            raise ValueError(f"Entry node '{spec.entry_node}' not found in graph")

        self._entry_points[spec.id] = spec
        logger.info(f"Registered entry point: {spec.id} -> {spec.entry_node}")

    def unregister_entry_point(self, entry_point_id: str) -> bool:
        """Unregister an entry point"""
        if self._running:
            raise RuntimeError("Cannot unregister entry points while runtime is running")

        if entry_point_id in self._entry_points:
            del self._entry_points[entry_point_id]
            return True
        return False

    async def start(self) -> None:
        """Start the agent runtime and all registered entry points"""
        if self._running:
            return

        async with self._lock:
            # Start storage
            await self._storage.start()

            # Create streams for each entry point
            for ep_id, spec in self._entry_points.items():
                stream = ExecutionStream(
                    stream_id=ep_id,
                    entry_spec=spec,
                    graph=self.graph,
                    goal=self.goal,
                    state_manager=self._state_manager,
                    storage=self._storage,
                    outcome_aggregator=self._outcome_aggregator,
                    event_bus=self._event_bus,
                    llm=self._llm,
                    tools=self._tools,
                    tool_executor=self._tool_executor,
                    result_retention_max=self._config.execution_result_max,
                    result_retention_ttl_seconds=self._config.execution_result_ttl_seconds,
                    runtime_log_store=self._runtime_log_store,
                    session_store=self._session_store,
                    checkpoint_config=self._checkpoint_config,
                    graph_id=self._graph_id,
                    accounts_prompt=self._accounts_prompt,
                    accounts_data=self._accounts_data,
                    tool_provider_map=self._tool_provider_map,
                )
                await stream.start()
                self._streams[ep_id] = stream

            # Subscribe event-driven entry points to EventBus
            from engine.runtime.event_bus import EventType as _ET

            for ep_id, spec in self._entry_points.items():
                if spec.trigger_type != "event":
                    continue

                tc = spec.trigger_config
                event_types = [_ET(et) for et in tc.get("event_types", [])]
                if not event_types:
                    logger.warning(
                        f"Entry point '{ep_id}' has trigger_type='event' "
                        "but no event_types in trigger_config"
                    )
                    continue

                # Capture ep_id and config in closure
                exclude_own = tc.get("exclude_own_graph", False)

                def _make_handler(entry_point_id: str, _exclude_own: bool):
                    _persistent_session_id: str | None = None

                    async def _on_event(event):
                        nonlocal _persistent_session_id
                        if not self._running or entry_point_id not in self._streams:
                            return
                        # Skip events originating from this graph's own
                        # executions (e.g. guardian should not fire on
                        # engine_coder failures — only secondary graphs).
                        if _exclude_own and event.graph_id == self._graph_id:
                            return
                        ep_spec = self._entry_points.get(entry_point_id)
                        is_isolated = ep_spec and ep_spec.isolation_level == "isolated"
                        if is_isolated:
                            if _persistent_session_id:
                                session_state = {"resume_session_id": _persistent_session_id}
                            else:
                                session_state = None
                        else:
                            # Run in the same session as the primary entry
                            # point so memory (e.g. user-defined rules) is
                            # shared and logs land in one session directory.
                            session_state = self._get_primary_session_state(
                                exclude_entry_point=entry_point_id
                            )
                        exec_id = await self.trigger(
                            entry_point_id,
                            {"event": event.to_dict()},
                            session_state=session_state,
                        )
                        if not _persistent_session_id and is_isolated:
                            _persistent_session_id = exec_id

                    return _on_event

                sub_id = self._event_bus.subscribe(
                    event_types=event_types,
                    handler=_make_handler(ep_id, exclude_own),
                    filter_stream=tc.get("filter_stream"),
                    filter_node=tc.get("filter_node"),
                    filter_graph=tc.get("filter_graph"),
                )
                self._event_subscriptions.append(sub_id)

            # Start timer-driven entry points
            for ep_id, spec in self._entry_points.items():
                if spec.trigger_type != "timer":
                    continue

                tc = spec.trigger_config
                cron_expr = tc.get("cron")
                interval = tc.get("interval_minutes")
                run_immediately = tc.get("run_immediately", False)

                if cron_expr:
                    # Cron expression mode — takes priority over interval_minutes
                    try:
                        from croniter import croniter

                        # Validate the expression upfront
                        if not croniter.is_valid(cron_expr):
                            raise ValueError(f"Invalid cron expression: {cron_expr}")
                    except (ImportError, ValueError) as e:
                        logger.warning(
                            "Entry point '%s' has invalid cron config: %s",
                            ep_id,
                            e,
                        )
                        continue

                    def _make_cron_timer(
                        entry_point_id: str,
                        expr: str,
                        immediate: bool,
                        idle_timeout: float = 300,
                    ):
                        async def _cron_loop():
                            from croniter import croniter

                            _persistent_session_id: str | None = None
                            if not immediate:
                                cron = croniter(expr, datetime.now())
                                next_dt = cron.get_next(datetime)
                                sleep_secs = (next_dt - datetime.now()).total_seconds()
                                self._timer_next_fire[entry_point_id] = (
                                    time.monotonic() + sleep_secs
                                )
                                await asyncio.sleep(max(0, sleep_secs))
                            while self._running:
                                # Calculate next fire time upfront (used by skip paths too)
                                cron = croniter(expr, datetime.now())
                                next_dt = cron.get_next(datetime)
                                sleep_secs = (next_dt - datetime.now()).total_seconds()

                                # Gate: skip tick if timers are explicitly paused
                                if self._timers_paused:
                                    logger.debug(
                                        "Cron '%s': paused, skipping tick",
                                        entry_point_id,
                                    )
                                    self._timer_next_fire[entry_point_id] = (
                                        time.monotonic() + sleep_secs
                                    )
                                    await asyncio.sleep(max(0, sleep_secs))
                                    continue

                                # Gate: skip tick if ANY stream is actively working.
                                # If the execution is idle (no LLM/tool activity
                                # beyond idle_timeout) let the timer proceed —
                                # execute() will cancel the stale execution.
                                _any_active = False
                                _min_idle = float("inf")
                                for _s in self._streams.values():
                                    if _s.active_execution_ids:
                                        _any_active = True
                                        _idle = _s.agent_idle_seconds
                                        if _idle < _min_idle:
                                            _min_idle = _idle
                                logger.info(
                                    "Cron '%s': gate — active=%s, idle=%.1fs, timeout=%ds",
                                    entry_point_id,
                                    _any_active,
                                    _min_idle,
                                    idle_timeout,
                                )
                                if _any_active and _min_idle < idle_timeout:
                                    logger.info(
                                        "Cron '%s': agent actively working, skipping tick",
                                        entry_point_id,
                                    )
                                    self._timer_next_fire[entry_point_id] = (
                                        time.monotonic() + sleep_secs
                                    )
                                    await asyncio.sleep(max(0, sleep_secs))
                                    continue

                                self._timer_next_fire.pop(entry_point_id, None)
                                try:
                                    ep_spec = self._entry_points.get(entry_point_id)
                                    is_isolated = ep_spec and ep_spec.isolation_level == "isolated"
                                    if is_isolated:
                                        if _persistent_session_id:
                                            session_state = {
                                                "resume_session_id": _persistent_session_id
                                            }
                                        else:
                                            session_state = None
                                    else:
                                        session_state = self._get_primary_session_state(
                                            exclude_entry_point=entry_point_id
                                        )
                                        # Gate: skip tick if no active session
                                        if session_state is None:
                                            logger.debug(
                                                "Cron '%s': no active session, skipping",
                                                entry_point_id,
                                            )
                                            self._timer_next_fire[entry_point_id] = (
                                                time.monotonic() + sleep_secs
                                            )
                                            await asyncio.sleep(max(0, sleep_secs))
                                            continue

                                    exec_id = await self.trigger(
                                        entry_point_id,
                                        {
                                            "event": {
                                                "source": "timer",
                                                "reason": "scheduled",
                                            }
                                        },
                                        session_state=session_state,
                                    )
                                    if not _persistent_session_id and is_isolated:
                                        _persistent_session_id = exec_id
                                    logger.info(
                                        "Cron fired for entry point '%s' (expr: %s)",
                                        entry_point_id,
                                        expr,
                                    )
                                except Exception:
                                    logger.error(
                                        "Cron trigger failed for '%s'",
                                        entry_point_id,
                                        exc_info=True,
                                    )
                                # Calculate next fire from now
                                cron = croniter(expr, datetime.now())
                                next_dt = cron.get_next(datetime)
                                sleep_secs = (next_dt - datetime.now()).total_seconds()
                                self._timer_next_fire[entry_point_id] = (
                                    time.monotonic() + sleep_secs
                                )
                                await asyncio.sleep(max(0, sleep_secs))

                        return _cron_loop

                    task = asyncio.create_task(
                        _make_cron_timer(
                            ep_id,
                            cron_expr,
                            run_immediately,
                            idle_timeout=tc.get("idle_timeout_seconds", 300),
                        )()
                    )
                    self._timer_tasks.append(task)
                    logger.info(
                        "Started cron timer for entry point '%s' with expression '%s'%s",
                        ep_id,
                        cron_expr,
                        " (immediate first run)" if run_immediately else "",
                    )

                elif interval and interval > 0:
                    # Fixed interval mode (original behavior)
                    def _make_timer(
                        entry_point_id: str,
                        mins: float,
                        immediate: bool,
                        idle_timeout: float = 300,
                    ):
                        async def _timer_loop():
                            interval_secs = mins * 60
                            _persistent_session_id: str | None = None
                            if not immediate:
                                self._timer_next_fire[entry_point_id] = (
                                    time.monotonic() + interval_secs
                                )
                                await asyncio.sleep(interval_secs)
                            while self._running:
                                # Gate: skip tick if timers are explicitly paused
                                if self._timers_paused:
                                    logger.debug(
                                        "Timer '%s': paused, skipping tick",
                                        entry_point_id,
                                    )
                                    self._timer_next_fire[entry_point_id] = (
                                        time.monotonic() + interval_secs
                                    )
                                    await asyncio.sleep(interval_secs)
                                    continue

                                # Gate: skip tick if agent is actively working.
                                # Gate: skip tick if ANY stream is actively working.
                                _any_active = False
                                _min_idle = float("inf")
                                for _s in self._streams.values():
                                    if _s.active_execution_ids:
                                        _any_active = True
                                        _idle = _s.agent_idle_seconds
                                        if _idle < _min_idle:
                                            _min_idle = _idle
                                logger.info(
                                    "Timer '%s': gate — active=%s, idle=%.1fs, timeout=%ds",
                                    entry_point_id,
                                    _any_active,
                                    _min_idle,
                                    idle_timeout,
                                )
                                if _any_active and _min_idle < idle_timeout:
                                    logger.info(
                                        "Timer '%s': agent actively working, skipping tick",
                                        entry_point_id,
                                    )
                                    self._timer_next_fire[entry_point_id] = (
                                        time.monotonic() + interval_secs
                                    )
                                    await asyncio.sleep(interval_secs)
                                    continue

                                self._timer_next_fire.pop(entry_point_id, None)
                                try:
                                    ep_spec = self._entry_points.get(entry_point_id)
                                    is_isolated = ep_spec and ep_spec.isolation_level == "isolated"
                                    if is_isolated:
                                        if _persistent_session_id:
                                            session_state = {
                                                "resume_session_id": _persistent_session_id
                                            }
                                        else:
                                            session_state = None
                                    else:
                                        session_state = self._get_primary_session_state(
                                            exclude_entry_point=entry_point_id
                                        )
                                        # Gate: skip tick if no active session
                                        if session_state is None:
                                            logger.debug(
                                                "Timer '%s': no active session, skipping",
                                                entry_point_id,
                                            )
                                            self._timer_next_fire[entry_point_id] = (
                                                time.monotonic() + interval_secs
                                            )
                                            await asyncio.sleep(interval_secs)
                                            continue

                                    exec_id = await self.trigger(
                                        entry_point_id,
                                        {
                                            "event": {
                                                "source": "timer",
                                                "reason": "scheduled",
                                            }
                                        },
                                        session_state=session_state,
                                    )
                                    if not _persistent_session_id and is_isolated:
                                        _persistent_session_id = exec_id
                                    logger.info(
                                        "Timer fired for entry point '%s' (next in %s min)",
                                        entry_point_id,
                                        mins,
                                    )
                                except Exception:
                                    logger.error(
                                        "Timer trigger failed for '%s'",
                                        entry_point_id,
                                        exc_info=True,
                                    )
                                self._timer_next_fire[entry_point_id] = (
                                    time.monotonic() + interval_secs
                                )
                                await asyncio.sleep(interval_secs)

                        return _timer_loop

                    task = asyncio.create_task(
                        _make_timer(
                            ep_id,
                            interval,
                            run_immediately,
                            idle_timeout=tc.get("idle_timeout_seconds", 300),
                        )()
                    )
                    self._timer_tasks.append(task)
                    logger.info(
                        "Started timer for entry point '%s' every %s min%s",
                        ep_id,
                        interval,
                        " (immediate first run)" if run_immediately else "",
                    )

                else:
                    logger.warning(
                        "Entry point '%s' has trigger_type='timer' "
                        "but no 'cron' or valid 'interval_minutes' in trigger_config",
                        ep_id,
                    )

            # Register primary graph
            self._graphs[self._graph_id] = _GraphRegistration(
                graph=self.graph,
                goal=self.goal,
                entry_points=dict(self._entry_points),
                streams=dict(self._streams),
                storage_subpath="",
                event_subscriptions=list(self._event_subscriptions),
                timer_tasks=list(self._timer_tasks),
                timer_next_fire=self._timer_next_fire,
            )

            self._running = True
            self._timers_paused = False
            logger.info(f"AgentRuntime started with {len(self._streams)} streams")

    async def stop(self) -> None:
        """Stop the agent runtime and all streams"""
        if not self._running:
            return

        async with self._lock:
            # Stop secondary graphs first
            secondary_ids = [gid for gid in self._graphs if gid != self._graph_id]
            for gid in secondary_ids:
                await self._teardown_graph(gid)

            # Cancel primary timer tasks
            for task in self._timer_tasks:
                task.cancel()
            self._timer_tasks.clear()

            # Unsubscribe primary event-driven entry points
            for sub_id in self._event_subscriptions:
                self._event_bus.unsubscribe(sub_id)
            self._event_subscriptions.clear()

            # Stop all primary streams
            for stream in self._streams.values():
                await stream.stop()

            self._streams.clear()
            self._graphs.clear()

            # Stop storage
            await self._storage.stop()

            self._running = False
            logger.info("AgentRuntime stopped")

    def pause_timers(self) -> None:
        """Pause all timer-driven entry points"""
        self._timers_paused = True
        logger.info("Timers paused")

    def resume_timers(self) -> None:
        """Resume timer-driven entry points after a pause"""
        self._timers_paused = False
        logger.info("Timers resumed")

    def _resolve_stream(
        self,
        entry_point_id: str,
        graph_id: str | None = None,
    ) -> ExecutionStream | None:
        """Find the stream for an entry point, searching the active graph first"""
        if graph_id:
            reg = self._graphs.get(graph_id)
            return reg.streams.get(entry_point_id) if reg else None

        # Active graph
        target = self._active_graph_id
        if target != self._graph_id:
            reg = self._graphs.get(target)
            if reg:
                stream = reg.streams.get(entry_point_id)
                if stream is not None:
                    return stream

        # Primary graph (also stored in self._streams)
        return self._streams.get(entry_point_id)

    async def trigger(
        self,
        entry_point_id: str,
        input_data: dict[str, Any],
        correlation_id: str | None = None,
        session_state: dict[str, Any] | None = None,
        graph_id: str | None = None,
    ) -> str:
        """Trigger execution at a specific entry point"""
        if not self._running:
            raise RuntimeError("AgentRuntime is not running")

        stream = self._resolve_stream(entry_point_id, graph_id)
        if stream is None:
            raise ValueError(f"Entry point '{entry_point_id}' not found")

        return await stream.execute(input_data, correlation_id, session_state)

    async def trigger_and_wait(
        self,
        entry_point_id: str,
        input_data: dict[str, Any],
        timeout: float | None = None,
        session_state: dict[str, Any] | None = None,
    ) -> ExecutionResult | None:
        """Trigger execution and wait for completion"""
        exec_id = await self.trigger(entry_point_id, input_data, session_state=session_state)
        stream = self._resolve_stream(entry_point_id)
        if stream is None:
            raise ValueError(f"Entry point '{entry_point_id}' not found")
        return await stream.wait_for_completion(exec_id, timeout)

    # === MULTI-GRAPH MANAGEMENT ===

    async def add_graph(
        self,
        graph_id: str,
        graph: "GraphSpec",
        goal: "Goal",
        entry_points: dict[str, EntryPointSpec],
        storage_subpath: str | None = None,
    ) -> None:
        """Load a secondary graph into this runtime session"""
        if graph_id in self._graphs:
            raise ValueError(f"Graph '{graph_id}' already registered")

        subpath = storage_subpath or f"graphs/{graph_id}"

        # Validate entry nodes exist in graph
        for _ep_id, spec in entry_points.items():
            if graph.get_node(spec.entry_node) is None:
                raise ValueError(f"Entry node '{spec.entry_node}' not found in graph '{graph_id}'")

        # Secondary graphs get their own SessionStore AND RuntimeLogStore
        # so their sessions and logs don't pollute the worker's directories.
        graph_base = self._session_store.base_path / subpath
        graph_session_store = SessionStore(graph_base)
        graph_log_store = RuntimeLogStore(graph_base / "runtime_logs")

        # Create streams for each entry point
        streams: dict[str, ExecutionStream] = {}
        for ep_id, spec in entry_points.items():
            stream = ExecutionStream(
                stream_id=f"{graph_id}::{ep_id}",
                entry_spec=spec,
                graph=graph,
                goal=goal,
                state_manager=self._state_manager,
                storage=self._storage,
                outcome_aggregator=self._outcome_aggregator,
                event_bus=self._event_bus,
                llm=self._llm,
                tools=self._tools,
                tool_executor=self._tool_executor,
                result_retention_max=self._config.execution_result_max,
                result_retention_ttl_seconds=self._config.execution_result_ttl_seconds,
                runtime_log_store=graph_log_store,
                session_store=graph_session_store,
                checkpoint_config=self._checkpoint_config,
                graph_id=graph_id,
                accounts_prompt=self._accounts_prompt,
                accounts_data=self._accounts_data,
                tool_provider_map=self._tool_provider_map,
            )
            if self._running:
                await stream.start()
            streams[ep_id] = stream

        # Set up event-driven subscriptions
        from engine.runtime.event_bus import EventType as _ET

        event_subs: list[str] = []
        for ep_id, spec in entry_points.items():
            if spec.trigger_type != "event":
                continue
            tc = spec.trigger_config
            event_types = [_ET(et) for et in tc.get("event_types", [])]
            if not event_types:
                logger.warning(
                    "Entry point '%s::%s' has trigger_type='event' "
                    "but no event_types in trigger_config",
                    graph_id,
                    ep_id,
                )
                continue

            namespaced_ep = f"{graph_id}::{ep_id}"
            exclude_own = tc.get("exclude_own_graph", False)

            def _make_handler(entry_point_id: str, gid: str, _exclude_own: bool):
                _persistent_session_id: str | None = None

                async def _on_event(event):
                    nonlocal _persistent_session_id
                    if not self._running or gid not in self._graphs:
                        return
                    # Skip events from this graph's own executions
                    if _exclude_own and event.graph_id == gid:
                        return
                    reg = self._graphs[gid]
                    local_ep = entry_point_id.split("::", 1)[-1]
                    stream = reg.streams.get(local_ep)
                    if stream is None:
                        return
                    ep_spec = reg.entry_points.get(local_ep)
                    is_isolated = ep_spec and ep_spec.isolation_level == "isolated"
                    if is_isolated:
                        if _persistent_session_id:
                            session_state = {"resume_session_id": _persistent_session_id}
                        else:
                            session_state = None
                    else:
                        session_state = self._get_primary_session_state(
                            local_ep,
                            source_graph_id=gid,
                        )
                    exec_id = await stream.execute(
                        {"event": event.to_dict()},
                        session_state=session_state,
                    )
                    if not _persistent_session_id and is_isolated:
                        _persistent_session_id = exec_id

                return _on_event

            sub_id = self._event_bus.subscribe(
                event_types=event_types,
                handler=_make_handler(namespaced_ep, graph_id, exclude_own),
                filter_stream=tc.get("filter_stream"),
                filter_node=tc.get("filter_node"),
                filter_graph=tc.get("filter_graph"),
            )
            event_subs.append(sub_id)

        # Set up timer-driven entry points
        timer_tasks: list[asyncio.Task] = []
        timer_next_fire: dict[str, float] = {}
        for ep_id, spec in entry_points.items():
            if spec.trigger_type != "timer":
                continue
            tc = spec.trigger_config
            interval = tc.get("interval_minutes")
            run_immediately = tc.get("run_immediately", False)

            if interval and interval > 0 and self._running:
                logger.info(
                    "Creating timer for '%s::%s': interval=%s min, immediate=%s, loop=%s",
                    graph_id,
                    ep_id,
                    interval,
                    run_immediately,
                    id(asyncio.get_event_loop()),
                )

                def _make_timer(
                    gid: str,
                    local_ep: str,
                    mins: float,
                    immediate: bool,
                    idle_timeout: float = 300,
                ):
                    async def _timer_loop():
                        interval_secs = mins * 60
                        # For isolated entry points, reuse ONE session across
                        # all timer ticks so conversation_mode="continuous"
                        # actually works and we don't create N sessions.
                        _persistent_session_id: str | None = None

                        logger.info(
                            "Timer loop started for '%s::%s' (sleep %ss)",
                            gid,
                            local_ep,
                            interval_secs,
                        )
                        if not immediate:
                            timer_next_fire[local_ep] = time.monotonic() + interval_secs
                            await asyncio.sleep(interval_secs)
                        while self._running and gid in self._graphs:
                            # Gate: skip tick if timers are explicitly paused
                            if self._timers_paused:
                                logger.debug(
                                    "Timer '%s::%s': paused, skipping tick",
                                    gid,
                                    local_ep,
                                )
                                timer_next_fire[local_ep] = time.monotonic() + interval_secs
                                await asyncio.sleep(interval_secs)
                                continue

                            # Gate: skip tick if ANY stream in this graph is actively working.
                            _reg = self._graphs.get(gid)
                            _any_active = False
                            _min_idle = float("inf")
                            if _reg:
                                for _sid, _s in _reg.streams.items():
                                    if _s.active_execution_ids:
                                        _any_active = True
                                        _idle = _s.agent_idle_seconds
                                        if _idle < _min_idle:
                                            _min_idle = _idle
                            logger.info(
                                "Timer '%s::%s': gate — active=%s, idle=%.1fs, timeout=%ds",
                                gid,
                                local_ep,
                                _any_active,
                                _min_idle,
                                idle_timeout,
                            )
                            if _any_active and _min_idle < idle_timeout:
                                logger.info(
                                    "Timer '%s::%s': agent actively working, skipping tick",
                                    gid,
                                    local_ep,
                                )
                                timer_next_fire[local_ep] = time.monotonic() + interval_secs
                                await asyncio.sleep(interval_secs)
                                continue

                            logger.info("Timer firing for '%s::%s'", gid, local_ep)
                            timer_next_fire.pop(local_ep, None)
                            try:
                                reg = self._graphs.get(gid)
                                if not reg:
                                    logger.warning("Timer: no reg for '%s', stopping", gid)
                                    break
                                stream = reg.streams.get(local_ep)
                                if not stream:
                                    logger.warning(
                                        "Timer: no stream '%s' in '%s', stopping", local_ep, gid
                                    )
                                    break
                                # Isolated entry points get their own session;
                                # shared ones join the primary session.
                                ep_spec = reg.entry_points.get(local_ep)
                                if ep_spec and ep_spec.isolation_level == "isolated":
                                    if _persistent_session_id:
                                        session_state = {
                                            "resume_session_id": _persistent_session_id
                                        }
                                    else:
                                        session_state = None
                                else:
                                    session_state = self._get_primary_session_state(
                                        local_ep, source_graph_id=gid
                                    )
                                    # Gate: skip tick if no active session
                                    if session_state is None:
                                        logger.debug(
                                            "Timer '%s::%s': no active session, skipping",
                                            gid,
                                            local_ep,
                                        )
                                        timer_next_fire[local_ep] = time.monotonic() + interval_secs
                                        await asyncio.sleep(interval_secs)
                                        continue

                                exec_id = await stream.execute(
                                    {"event": {"source": "timer", "reason": "scheduled"}},
                                    session_state=session_state,
                                )
                                # Remember session ID for reuse on next tick
                                if (
                                    not _persistent_session_id
                                    and ep_spec
                                    and ep_spec.isolation_level == "isolated"
                                ):
                                    _persistent_session_id = exec_id
                            except Exception:
                                logger.error(
                                    "Timer trigger failed for '%s::%s'",
                                    gid,
                                    local_ep,
                                    exc_info=True,
                                )
                            timer_next_fire[local_ep] = time.monotonic() + interval_secs
                            await asyncio.sleep(interval_secs)
                        logger.info("Timer loop exited for '%s::%s'", gid, local_ep)

                    return _timer_loop

                task = asyncio.create_task(
                    _make_timer(
                        graph_id,
                        ep_id,
                        interval,
                        run_immediately,
                        idle_timeout=tc.get("idle_timeout_seconds", 300),
                    )()
                )
                timer_tasks.append(task)
                logger.info("Timer task created for '%s::%s': %s", graph_id, ep_id, task)

        self._graphs[graph_id] = _GraphRegistration(
            graph=graph,
            goal=goal,
            entry_points=entry_points,
            streams=streams,
            storage_subpath=subpath,
            event_subscriptions=event_subs,
            timer_tasks=timer_tasks,
            timer_next_fire=timer_next_fire,
        )
        logger.info(
            "Added graph '%s' with %d entry points (%d streams)",
            graph_id,
            len(entry_points),
            len(streams),
        )

    async def remove_graph(self, graph_id: str) -> None:
        """Remove a secondary graph from this runtime session"""
        if graph_id == self._graph_id:
            raise ValueError("Cannot remove the primary graph")
        if graph_id not in self._graphs:
            raise ValueError(f"Graph '{graph_id}' not found")
        await self._teardown_graph(graph_id)
        logger.info("Removed graph '%s'", graph_id)

    async def _teardown_graph(self, graph_id: str) -> None:
        """Internal: stop and clean up all resources for a graph"""
        reg = self._graphs.pop(graph_id, None)
        if reg is None:
            return

        # Cancel timers
        for task in reg.timer_tasks:
            task.cancel()

        # Unsubscribe events
        for sub_id in reg.event_subscriptions:
            self._event_bus.unsubscribe(sub_id)

        # Stop streams
        for stream in reg.streams.values():
            await stream.stop()

        # Reset active graph if it was the removed one
        if self._active_graph_id == graph_id:
            self._active_graph_id = self._graph_id

    def list_graphs(self) -> list[str]:
        """Return all registered graph IDs (primary first)"""
        result = []
        if self._graph_id in self._graphs:
            result.append(self._graph_id)
        for gid in self._graphs:
            if gid != self._graph_id:
                result.append(gid)
        return result

    @property
    def graph_id(self) -> str:
        """The primary graph's ID"""
        return self._graph_id

    @property
    def active_graph_id(self) -> str:
        """The currently focused graph (for TUI routing)"""
        return self._active_graph_id

    @active_graph_id.setter
    def active_graph_id(self, value: str) -> None:
        if value not in self._graphs:
            raise ValueError(f"Graph '{value}' not registered")
        self._active_graph_id = value

    def get_active_graph(self) -> "GraphSpec":
        """Return the GraphSpec for the currently active graph"""
        if self._active_graph_id == self._graph_id:
            return self.graph
        reg = self._graphs.get(self._active_graph_id)
        if reg is not None:
            return reg.graph
        return self.graph

    @property
    def user_idle_seconds(self) -> float:
        """Seconds since the user last provided input"""
        if self._last_user_input_time == 0.0:
            return float("inf")
        return time.monotonic() - self._last_user_input_time

    @property
    def agent_idle_seconds(self) -> float:
        """Seconds since any stream last had activity (LLM call, tool call, etc.)"""
        min_idle = float("inf")
        for reg in self._graphs.values():
            for stream in reg.streams.values():
                idle = stream.agent_idle_seconds
                if idle < min_idle:
                    min_idle = idle
        return min_idle

    def get_graph_registration(self, graph_id: str) -> _GraphRegistration | None:
        """Get the registration for a specific graph (or None)"""
        return self._graphs.get(graph_id)

    def cancel_all_tasks(self, loop: asyncio.AbstractEventLoop) -> bool:
        """Cancel all running execution tasks across all graphs"""
        future = asyncio.run_coroutine_threadsafe(self.cancel_all_tasks_async(), loop)
        try:
            return future.result(timeout=5)
        except Exception:
            logger.warning("cancel_all_tasks: timed out or failed")
            return False

    async def cancel_all_tasks_async(self) -> bool:
        """Cancel all running execution tasks (runs on the agent loop)"""
        cancelled = False
        for gid in self.list_graphs():
            reg = self.get_graph_registration(gid)
            if reg:
                for stream in reg.streams.values():
                    for task in list(stream._execution_tasks.values()):
                        if task and not task.done():
                            task.cancel()
                            cancelled = True
        return cancelled

    def _get_primary_session_state(
        self,
        exclude_entry_point: str,
        *,
        source_graph_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Build session_state so an async entry point runs in the primary"""
        import json as _json

        # Determine which memory keys the async entry node needs.
        allowed_keys: set[str] | None = None
        # Look up the entry node from the correct graph
        src_graph_id = source_graph_id or self._graph_id
        src_reg = self._graphs.get(src_graph_id)
        ep_spec = (
            src_reg.entry_points.get(exclude_entry_point)
            if src_reg
            else self._entry_points.get(exclude_entry_point)
        )
        if ep_spec:
            graph = src_reg.graph if src_reg else self.graph
            entry_node = graph.get_node(ep_spec.entry_node)
            if entry_node and entry_node.input_keys:
                allowed_keys = set(entry_node.input_keys)

        # Search primary graph's streams for an active session.
        # Skip isolated streams (e.g. health judge) — they have their own
        # session directories and must never be used as a shared session.
        all_streams: list[tuple[str, ExecutionStream]] = []
        for _gid, reg in self._graphs.items():
            for ep_id, stream in reg.streams.items():
                # Skip isolated entry points — they run in their own namespace
                ep_spec = reg.entry_points.get(ep_id)
                if ep_spec and getattr(ep_spec, "isolation_level", "shared") == "isolated":
                    continue
                all_streams.append((ep_id, stream))

        for ep_id, stream in all_streams:
            if ep_id == exclude_entry_point:
                continue
            for exec_id in stream.active_execution_ids:
                state_path = self._storage.base_path / "sessions" / exec_id / "state.json"
                try:
                    if state_path.exists():
                        data = _json.loads(state_path.read_text(encoding="utf-8"))
                        full_memory = data.get("memory", {})
                        if not full_memory:
                            continue
                        # Filter to only input keys so stale outputs
                        # from previous triggers don't leak through.
                        if allowed_keys is not None:
                            memory = {k: v for k, v in full_memory.items() if k in allowed_keys}
                        else:
                            memory = full_memory
                        if memory:
                            return {
                                "resume_session_id": exec_id,
                                "memory": memory,
                            }
                except Exception:
                    logger.debug(
                        "Could not read state.json for %s: skipping",
                        exec_id,
                        exc_info=True,
                    )
        return None

    async def inject_input(
        self,
        node_id: str,
        content: str,
        graph_id: str | None = None,
        *,
        is_client_input: bool = False,
    ) -> bool:
        """Inject user input into a running client-facing node"""
        # Track user presence
        self._last_user_input_time = time.monotonic()

        # Search target graph first
        target = graph_id or self._active_graph_id
        if target in self._graphs:
            for stream in self._graphs[target].streams.values():
                if await stream.inject_input(node_id, content, is_client_input=is_client_input):
                    return True

        # Then search all other graphs
        for gid, reg in self._graphs.items():
            if gid == target:
                continue
            for stream in reg.streams.values():
                if await stream.inject_input(node_id, content, is_client_input=is_client_input):
                    return True
        return False

    async def get_goal_progress(self) -> dict[str, Any]:
        """Evaluate goal progress across all streams"""
        return await self._outcome_aggregator.evaluate_goal_progress()

    async def cancel_execution(
        self,
        entry_point_id: str,
        execution_id: str,
        graph_id: str | None = None,
    ) -> bool:
        """Cancel a running execution"""
        stream = self._resolve_stream(entry_point_id, graph_id)
        if stream is None:
            return False
        return await stream.cancel_execution(execution_id)

    # === QUERY OPERATIONS ===

    def get_entry_points(self, graph_id: str | None = None) -> list[EntryPointSpec]:
        """Get entry points for a graph"""
        gid = graph_id or self._active_graph_id
        if gid == self._graph_id:
            return list(self._entry_points.values())
        reg = self._graphs.get(gid)
        if reg is not None:
            return list(reg.entry_points.values())
        # Fallback: primary graph
        return list(self._entry_points.values())

    def get_timer_next_fire_in(self, entry_point_id: str) -> float | None:
        """Return seconds until the next timer fire for *entry_point_id*"""
        mono = self._timer_next_fire.get(entry_point_id)
        if mono is not None:
            return max(0.0, mono - time.monotonic())
        for reg in self._graphs.values():
            mono = reg.timer_next_fire.get(entry_point_id)
            if mono is not None:
                return max(0.0, mono - time.monotonic())
        return None

    def get_stream(self, entry_point_id: str) -> ExecutionStream | None:
        """Get a specific execution stream"""
        return self._streams.get(entry_point_id)

    def find_awaiting_node(self) -> tuple[str | None, str | None]:
        """Find a node that is currently awaiting user input"""
        for graph_id, reg in self._graphs.items():
            for stream in reg.streams.values():
                for executor in stream._active_executors.values():
                    for node_id, node in executor.node_registry.items():
                        if getattr(node, "_awaiting_input", False):
                            return node_id, graph_id
        return None, None

    def get_execution_result(
        self,
        entry_point_id: str,
        execution_id: str,
        graph_id: str | None = None,
    ) -> ExecutionResult | None:
        """Get result of a completed execution"""
        stream = self._resolve_stream(entry_point_id, graph_id)
        if stream:
            return stream.get_result(execution_id)
        return None

    # === EVENT SUBSCRIPTIONS ===

    def subscribe_to_events(
        self,
        event_types: list,
        handler: Callable,
        filter_stream: str | None = None,
        filter_graph: str | None = None,
    ) -> str:
        """Subscribe to agent events"""
        return self._event_bus.subscribe(
            event_types=event_types,
            handler=handler,
            filter_stream=filter_stream,
            filter_graph=filter_graph,
        )

    def unsubscribe_from_events(self, subscription_id: str) -> bool:
        """Unsubscribe from events"""
        return self._event_bus.unsubscribe(subscription_id)

    # === STATS AND MONITORING ===

    def get_stats(self) -> dict:
        """Get comprehensive runtime statistics"""
        stream_stats = {}
        for ep_id, stream in self._streams.items():
            stream_stats[ep_id] = stream.get_stats()

        return {
            "running": self._running,
            "entry_points": len(self._entry_points),
            "streams": stream_stats,
            "goal_id": self.goal.id,
            "outcome_aggregator": self._outcome_aggregator.get_stats(),
            "event_bus": self._event_bus.get_stats(),
            "state_manager": self._state_manager.get_stats(),
        }

    def get_active_streams(self) -> list[dict[str, Any]]:
        """Return metadata for every stream that has active executions"""
        result: list[dict[str, Any]] = []
        for graph_id, reg in self._graphs.items():
            for ep_id, stream in reg.streams.items():
                active = stream.active_execution_ids
                if not active:
                    continue
                result.append(
                    {
                        "graph_id": graph_id,
                        "stream_id": stream.stream_id,
                        "entry_point_id": ep_id,
                        "active_execution_ids": active,
                        "is_awaiting_input": stream.is_awaiting_input,
                        "waiting_nodes": stream.get_waiting_nodes(),
                    }
                )
        return result

    def get_waiting_nodes(self) -> list[dict[str, Any]]:
        """Return all nodes currently blocked waiting for client input"""
        result: list[dict[str, Any]] = []
        for graph_id, reg in self._graphs.items():
            for _ep_id, stream in reg.streams.items():
                for waiting in stream.get_waiting_nodes():
                    result.append(
                        {
                            "graph_id": graph_id,
                            "stream_id": stream.stream_id,
                            **waiting,
                        }
                    )
        return result

    # === PROPERTIES ===

    @property
    def state_manager(self) -> SharedStateManager:
        """Access the shared state manager"""
        return self._state_manager

    @property
    def event_bus(self) -> EventBus:
        """Access the event bus"""
        return self._event_bus

    @property
    def outcome_aggregator(self) -> OutcomeAggregator:
        """Access the outcome aggregator"""
        return self._outcome_aggregator

    @property
    def timers_paused(self) -> bool:
        """True when timer-driven entry points are paused (e.g. by stop_worker)"""
        return self._timers_paused

    @property
    def is_running(self) -> bool:
        """Check if runtime is running"""
        return self._running


# === CONVENIENCE FACTORY ===


def create_agent_runtime(
    graph: "GraphSpec",
    goal: "Goal",
    storage_path: str | Path,
    entry_points: list[EntryPointSpec],
    llm: "LLMProvider | None" = None,
    tools: list["Tool"] | None = None,
    tool_executor: Callable | None = None,
    config: AgentRuntimeConfig | None = None,
    runtime_log_store: Any = None,
    enable_logging: bool = True,
    checkpoint_config: CheckpointConfig | None = None,
    graph_id: str | None = None,
    accounts_prompt: str = "",
    accounts_data: list[dict] | None = None,
    tool_provider_map: dict[str, str] | None = None,
    event_bus: "EventBus | None" = None,
) -> AgentRuntime:
    """Create and configure an AgentRuntime with entry points"""
    # Auto-create runtime log store if logging is enabled and not provided
    if enable_logging and runtime_log_store is None:
        from engine.runtime.runtime_log_store import RuntimeLogStore

        storage_path_obj = Path(storage_path) if isinstance(storage_path, str) else storage_path
        runtime_log_store = RuntimeLogStore(storage_path_obj / "runtime_logs")

    runtime = AgentRuntime(
        graph=graph,
        goal=goal,
        storage_path=storage_path,
        llm=llm,
        tools=tools,
        tool_executor=tool_executor,
        config=config,
        runtime_log_store=runtime_log_store,
        checkpoint_config=checkpoint_config,
        graph_id=graph_id,
        accounts_prompt=accounts_prompt,
        accounts_data=accounts_data,
        tool_provider_map=tool_provider_map,
        event_bus=event_bus,
    )

    for spec in entry_points:
        runtime.register_entry_point(spec)

    return runtime
