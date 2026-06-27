"""Graph pattern tests using mock nodes — no LLM calls."""

from __future__ import annotations

import pytest

from engine.graph.edge import EdgeCondition, EdgeSpec, GraphSpec
from engine.graph.executor import GraphExecutor
from engine.graph.goal import Goal
from engine.graph.node import NodeResult, NodeSpec


class _RuntimeStub:
    execution_id = ""

    def start_run(self, **kwargs: object) -> str:
        return "run-test"

    def end_run(self, **kwargs: object) -> None:
        return None

    def set_node(self, node_id: str) -> None:
        return None

    def decide(self, **kwargs: object) -> str:
        return "dec-0"

    def record_outcome(self, **kwargs: object) -> None:
        return None

    def report_problem(self, **kwargs: object) -> str:
        return ""


class _EchoNode:
    def validate_input(self, ctx):
        return []

    async def execute(self, ctx) -> NodeResult:
        text = ctx.input_data.get("text", "")
        return NodeResult(success=True, output={"echo": text})


class _AppendNode:
    def __init__(self, suffix: str) -> None:
        self.suffix = suffix

    def validate_input(self, ctx):
        return []

    async def execute(self, ctx) -> NodeResult:
        base = ctx.memory.read("echo") or ctx.input_data.get("text", "")
        return NodeResult(success=True, output={"echo": f"{base}{self.suffix}"})


def _graph_two_node_pipeline() -> GraphSpec:
    return GraphSpec(
        id="pipeline",
        goal_id="g1",
        nodes=[
            NodeSpec(
                id="n1",
                name="echo",
                description="echo",
                node_type="event_loop",
                input_keys=[],
                output_keys=["echo"],
            ),
            NodeSpec(
                id="n2",
                name="append",
                description="append",
                node_type="event_loop",
                input_keys=["echo"],
                output_keys=["echo"],
            ),
        ],
        edges=[
            EdgeSpec(id="e1", source="n1", target="n2", condition=EdgeCondition.ON_SUCCESS),
        ],
        entry_node="n1",
    )


@pytest.mark.asyncio
async def test_dummy_pipeline_echo_append() -> None:
    executor = GraphExecutor(
        runtime=_RuntimeStub(),
        node_registry={"n1": _EchoNode(), "n2": _AppendNode("!")},
    )
    goal = Goal(id="g1", name="pipeline", description="pipeline")
    result = await executor.execute(
        graph=_graph_two_node_pipeline(),
        goal=goal,
        input_data={"text": "hi"},
    )
    assert result.success is True
    assert result.path == ["n1", "n2"]


@pytest.mark.asyncio
async def test_dummy_branch_conditional() -> None:
    class _FailNode:
        def validate_input(self, ctx):
            return []

        async def execute(self, ctx) -> NodeResult:
            return NodeResult(success=False, output={})

    class _RecoveryNode:
        def validate_input(self, ctx):
            return []

        async def execute(self, ctx) -> NodeResult:
            return NodeResult(success=True, output={"recovered": True})

    graph = GraphSpec(
        id="branch",
        goal_id="g1",
        nodes=[
            NodeSpec(
                id="start",
                name="start",
                description="start",
                node_type="event_loop",
                input_keys=[],
                output_keys=[],
            ),
            NodeSpec(
                id="recover",
                name="recover",
                description="recover",
                node_type="event_loop",
                input_keys=[],
                output_keys=["recovered"],
            ),
        ],
        edges=[
            EdgeSpec(
                id="fail",
                source="start",
                target="recover",
                condition=EdgeCondition.ON_FAILURE,
            ),
        ],
        entry_node="start",
    )
    executor = GraphExecutor(
        runtime=_RuntimeStub(),
        node_registry={"start": _FailNode(), "recover": _RecoveryNode()},
    )
    goal = Goal(id="g1", name="branch", description="branch")
    result = await executor.execute(graph=graph, goal=goal)
    assert result.success is True
    assert "recover" in result.path
