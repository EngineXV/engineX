"""Queen Bee supervisor — primary interface for supervised worker sessions."""

from __future__ import annotations

from pathlib import Path

from engine.graph import Constraint, EdgeCondition, EdgeSpec, Goal, SuccessCriterion
from engine.graph.edge import GraphSpec

from .config import metadata
from .nodes import queen_node

# Worker graph loaded at session startup (Agreement Analysis pipeline).
supervised_worker_path = Path(__file__).resolve().parent.parent / "agreement_analysis"

queen_goal = Goal(
    id="queen-supervisor",
    name="Queen Supervisor",
    description="Primary operator interface; delegates and monitors the agreement analysis worker.",
    success_criteria=[
        SuccessCriterion(
            id="sc-delegate",
            description="Worker started when operator requests analysis",
            metric="worker_delegated",
            target="true",
            weight=0.5,
        ),
        SuccessCriterion(
            id="sc-monitor",
            description="Operator kept informed of worker status",
            metric="monitoring_active",
            target="true",
            weight=0.5,
        ),
    ],
    constraints=[
        Constraint(
            id="c-delegate",
            description="Do not fabricate agreement terms; delegate extraction to the worker",
            constraint_type="hard",
            category="quality",
        ),
    ],
)

# Queen node references lifecycle tools (registered at session setup).
nodes = [queen_node]

edges = [
    EdgeSpec(
        id="queen-loop",
        source="queen",
        target="queen",
        condition=EdgeCondition.ALWAYS,
        priority=1,
    ),
]

entry_node = "queen"
entry_points = {"queen": "queen"}
terminal_nodes = []
pause_nodes = []
loop_config = {
    "max_iterations": 100,
    "max_tool_calls_per_turn": 12,
    "max_history_tokens": 48000,
}

goal = queen_goal

graph = GraphSpec(
    id="queen-graph",
    goal_id=queen_goal.id,
    version=metadata.version,
    entry_node=entry_node,
    entry_points=entry_points,
    terminal_nodes=terminal_nodes,
    pause_nodes=pause_nodes,
    nodes=nodes,
    edges=edges,
    loop_config=loop_config,
)
