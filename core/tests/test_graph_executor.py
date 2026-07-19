"""
Tests for core GraphExecutor execution paths.
Focused on minimal success and failure scenarios.
"""

import pytest

from engine.graph.edge import GraphSpec
from engine.graph.executor import GraphExecutor
from engine.graph.goal import Goal
from engine.graph.node import NodeResult, NodeSpec


# ---- Dummy runtime (no real logging) ----
class DummyRuntime:
    execution_id = ""

    def start_run(self, **kwargs):
        return "run-1"

    def end_run(self, **kwargs):
        pass

    def report_problem(self, **kwargs):
        pass


# ---- Fake node that always succeeds ----
class SuccessNode:
    def validate_input(self, ctx):
        return []

    async def execute(self, ctx):
        return NodeResult(
            success=True,
            output={"result": 123},
            tokens_used=1,
            latency_ms=1,
        )


@pytest.mark.asyncio
async def test_executor_single_node_success():
    runtime = DummyRuntime()

    graph = GraphSpec(
        id="graph-1",
        goal_id="g1",
        nodes=[
            NodeSpec(
                id="n1",
                name="node1",
                description="test node",
                node_type="event_loop",
                input_keys=[],
                output_keys=["result"],
                max_retries=0,
            )
        ],
        edges=[],
        entry_node="n1",
    )

    executor = GraphExecutor(
        runtime=runtime,
        node_registry={"n1": SuccessNode()},
    )

    goal = Goal(
        id="g1",
        name="test-goal",
        description="simple test",
    )

    result = await executor.execute(graph=graph, goal=goal)

    assert result.success is True
    assert result.path == ["n1"]
    assert result.steps_executed == 1


# ---- Fake node that always fails ----
class FailingNode:
    def validate_input(self, ctx):
        return []

    async def execute(self, ctx):
        return NodeResult(
            success=False,
            error="boom",
            output={},
            tokens_used=0,
            latency_ms=0,
        )


@pytest.mark.asyncio
async def test_executor_single_node_failure():
    runtime = DummyRuntime()

    graph = GraphSpec(
        id="graph-2",
        goal_id="g2",
        nodes=[
            NodeSpec(
                id="n1",
                name="node1",
                description="failing node",
                node_type="event_loop",
                input_keys=[],
                output_keys=["result"],
                max_retries=0,
            )
        ],
        edges=[],
        entry_node="n1",
    )

    executor = GraphExecutor(
        runtime=runtime,
        node_registry={"n1": FailingNode()},
    )

    goal = Goal(
        id="g2",
        name="fail-goal",
        description="failure test",
    )

    result = await executor.execute(graph=graph, goal=goal)

    assert result.success is False
    assert result.error is not None
    assert result.path == ["n1"]


# ---- Fake event bus that records calls ----
class FakeEventBus:
    def __init__(self):
        self.events = []

    async def emit_node_loop_started(self, **kwargs):
        self.events.append(("started", kwargs))

    async def emit_node_loop_completed(self, **kwargs):
        self.events.append(("completed", kwargs))

    async def emit_edge_traversed(self, **kwargs):
        self.events.append(("edge_traversed", kwargs))

    async def emit_execution_paused(self, **kwargs):
        self.events.append(("execution_paused", kwargs))

    async def emit_execution_resumed(self, **kwargs):
        self.events.append(("execution_resumed", kwargs))

    async def emit_node_retry(self, **kwargs):
        self.events.append(("node_retry", kwargs))

    async def emit_node_started(self, **kwargs):
        self.events.append(("node_started", kwargs))

    async def emit_node_failed(self, **kwargs):
        self.events.append(("node_failed", kwargs))

    async def emit_node_hitl_paused(self, **kwargs):
        self.events.append(("node_hitl_paused", kwargs))


@pytest.mark.asyncio

# ---- Fake event_loop node (registered, so executor won't emit for it) ----
class FakeEventLoopNode:
    def validate_input(self, ctx):
        return []

    async def execute(self, ctx):
        return NodeResult(success=True, output={"result": "loop-done"}, tokens_used=1, latency_ms=1)


@pytest.mark.asyncio
async def test_executor_skips_events_for_event_loop_nodes():
    """Executor should NOT emit events for event_loop nodes (they emit their own)."""
    runtime = DummyRuntime()
    event_bus = FakeEventBus()

    graph = GraphSpec(
        id="graph-el",
        goal_id="g-el",
        nodes=[
            NodeSpec(
                id="el1",
                name="event-loop-node",
                description="event loop node",
                node_type="event_loop",
                input_keys=[],
                output_keys=["result"],
                max_retries=0,
            ),
        ],
        edges=[],
        entry_node="el1",
    )

    executor = GraphExecutor(
        runtime=runtime,
        node_registry={"el1": FakeEventLoopNode()},
        event_bus=event_bus,
        stream_id="test-stream",
    )

    goal = Goal(id="g-el", name="el-test", description="test event_loop guard")
    result = await executor.execute(graph=graph, goal=goal)

    assert result.success is True
    # No events should have been emitted — event_loop nodes are skipped
    assert len(event_bus.events) == 0


@pytest.mark.asyncio
async def test_executor_no_events_without_event_bus():
    """Executor should work fine without an event bus (backward compat)."""
    runtime = DummyRuntime()

    graph = GraphSpec(
        id="graph-nobus",
        goal_id="g-nobus",
        nodes=[
            NodeSpec(
                id="n1",
                name="node1",
                description="test node",
                node_type="event_loop",
                input_keys=[],
                output_keys=["result"],
                max_retries=0,
            )
        ],
        edges=[],
        entry_node="n1",
    )

    # No event_bus passed — should not crash
    executor = GraphExecutor(
        runtime=runtime,
        node_registry={"n1": SuccessNode()},
    )

    goal = Goal(id="g-nobus", name="nobus-test", description="no event bus")
    result = await executor.execute(graph=graph, goal=goal)

    assert result.success is True


class DummyRuntimeLogger:
    """Captures node event logs for testing."""

    def __init__(self):
        self.events = []

    def start_run(self, goal_id="", session_id=""):
        return session_id or "test-run"

    def log_node_event(
        self,
        node_id="",
        node_name="",
        event_type=None,
        duration_ms=0,
        attempt=1,
        error="",
        execution_id="",
    ):
        self.events.append(
            {
                "node_id": node_id,
                "node_name": node_name,
                "event_type": event_type.value if event_type else None,
                "duration_ms": duration_ms,
                "attempt": attempt,
                "error": error,
            }
        )

    def ensure_node_logged(self, **kwargs):
        pass

    async def end_run(self, **kwargs):
        pass


@pytest.mark.asyncio
async def test_executor_emits_node_events_started_completed():
    """Executor emits STARTED and COMPLETED node events for non-event_loop nodes."""
    runtime = DummyRuntime()
    runtime_logger = DummyRuntimeLogger()
    event_bus = FakeEventBus()

    graph = GraphSpec(
        id="graph-events",
        goal_id="g-events",
        nodes=[
            NodeSpec(
                id="n1",
                name="node1",
                description="test node",
                node_type="function",  # non-event_loop
                input_keys=[],
                output_keys=["result"],
                max_retries=0,
            )
        ],
        edges=[],
        entry_node="n1",
    )

    executor = GraphExecutor(
        runtime=runtime,
        node_registry={"n1": SuccessNode()},
        event_bus=event_bus,
        runtime_logger=runtime_logger,
        stream_id="test-stream",
    )

    goal = Goal(id="g-events", name="events-test", description="node events")
    result = await executor.execute(graph=graph, goal=goal)

    assert result.success is True

    # Check runtime_logger captured STARTED and COMPLETED
    started = [e for e in runtime_logger.events if e["event_type"] == "started"]
    completed = [e for e in runtime_logger.events if e["event_type"] == "completed"]
    assert len(started) == 1
    assert started[0]["node_id"] == "n1"
    assert len(completed) == 1
    assert completed[0]["node_id"] == "n1"

    # Check event_bus captured NODE_LOOP_STARTED and NODE_LOOP_COMPLETED
    assert any(e[0] == "started" for e in event_bus.events)
    assert any(e[0] == "completed" for e in event_bus.events)


@pytest.mark.asyncio
async def test_executor_node_events_failure_and_retry():
    """Executor emits STARTED, RETRY, and FAILED events on node failure + retry."""
    runtime = DummyRuntime()
    runtime_logger = DummyRuntimeLogger()
    event_bus = FakeEventBus()

    graph = GraphSpec(
        id="graph-fail",
        goal_id="g-fail",
        nodes=[
            NodeSpec(
                id="n1",
                name="failing-node",
                description="failing node with retry",
                node_type="function",
                input_keys=[],
                output_keys=["result"],
                max_retries=2,
            )
        ],
        edges=[],
        entry_node="n1",
    )

    executor = GraphExecutor(
        runtime=runtime,
        node_registry={"n1": FailingNode()},
        event_bus=event_bus,
        runtime_logger=runtime_logger,
        stream_id="test-stream",
    )

    goal = Goal(id="g-fail", name="fail-test", description="failure + retry")
    result = await executor.execute(graph=graph, goal=goal)

    assert result.success is False

    # Check runtime_logger captured all four transition types
    started = [e for e in runtime_logger.events if e["event_type"] == "started"]
    retries = [e for e in runtime_logger.events if e["event_type"] == "retry"]
    failed = [e for e in runtime_logger.events if e["event_type"] == "failed"]

    # max_retries=2 → 1 initial start + 1 retry start = 2 starts, 1 retry, 1 failed
    assert len(started) == 2
    assert len(retries) == 1
    assert len(failed) == 1

    assert started[0]["node_id"] == "n1"
    assert started[0]["attempt"] == 1
    assert started[1]["attempt"] == 2
    assert all(r["node_id"] == "n1" for r in retries)
    assert failed[0]["node_id"] == "n1"

    # Retry attempt should be 2nd attempt
    assert retries[0]["attempt"] == 2
    assert "boom" in retries[0]["error"]

    # Check event_bus captured retry events
    retry_events = [e for e in event_bus.events if e[0] == "node_retry"]
    assert len(retry_events) == 1
    assert retry_events[0][1]["retry_count"] == 1
