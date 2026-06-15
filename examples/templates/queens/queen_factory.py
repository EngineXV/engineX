"""Shared Queen Bee graph builder for department supervisors."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from engine.graph import Constraint, EdgeCondition, EdgeSpec, Goal, NodeSpec, SuccessCriterion
from engine.graph.edge import GraphSpec

if TYPE_CHECKING:
    from dataclasses import dataclass as dc

    @dataclass
    class QueenMetadata:
        name: str
        version: str
        description: str
        intro_message: str
        queen_bee: bool
        queen_name: str
        department: str
        role_title: str
        domain_focus: str


def _templates_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _build_system_prompt(metadata: QueenMetadata) -> str:
    return f"""\
You are {metadata.queen_name}, Queen Bee and {metadata.role_title} at Engine.

**Department focus:** {metadata.domain_focus}

**Your role**
- You are the operator's primary contact for {metadata.department.lower()} work. Be concise, professional, and warm.
- You supervise a worker agent that handles detailed agreement analysis — delegate extraction and review to the worker.

**Tools**
- `start_worker(task)` — begin work. Pass the operator's request or pasted agreement text.
- `get_worker_status()` — check if the worker is running or waiting for input.
- `inject_worker_message(message)` — forward a message to the worker (e.g. approval or more text).
- `stop_worker()` — cancel a running worker execution.

**Workflow**
1. Greet the operator briefly on first contact as {metadata.queen_name}.
2. When they describe a task or paste agreement text, call `start_worker` with that content.
3. After starting, stay quiet unless they ask for status or the worker needs their input.
4. If the worker is waiting for human review, tell the operator to reply in chat or use \
`inject_worker_message` with their approval/edits.

Never invent contract terms. Never repeat the same tool call with identical arguments.
"""


def build_queen_exports(metadata: QueenMetadata) -> dict:
    """Return module-level exports for a department Queen agent."""
    worker_path = _templates_root() / "agreement_analysis"

    queen_node = NodeSpec(
        id="queen",
        name=metadata.queen_name,
        description=f"{metadata.role_title} — delegates to the worker and monitors progress.",
        node_type="event_loop",
        client_facing=True,
        input_keys=["greeting"],
        output_keys=[],
        system_prompt=_build_system_prompt(metadata),
        tools=["start_worker", "get_worker_status", "inject_worker_message", "stop_worker"],
    )

    queen_goal = Goal(
        id=f"queen-{metadata.department.lower().replace(' ', '-').replace('&', 'and')}",
        name=metadata.queen_name,
        description=metadata.description,
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

    graph = GraphSpec(
        id=f"queen-{metadata.queen_name.lower()}-graph",
        goal_id=queen_goal.id,
        version=metadata.version,
        entry_node="queen",
        entry_points={"queen": "queen"},
        terminal_nodes=[],
        pause_nodes=[],
        nodes=nodes,
        edges=edges,
        loop_config={
            "max_iterations": 100,
            "max_tool_calls_per_turn": 12,
            "max_history_tokens": 48000,
        },
    )

    return {
        "metadata": metadata,
        "supervised_worker_path": worker_path,
        "goal": queen_goal,
        "queen_goal": queen_goal,
        "nodes": nodes,
        "edges": edges,
        "entry_node": "queen",
        "entry_points": {"queen": "queen"},
        "terminal_nodes": [],
        "pause_nodes": [],
        "loop_config": graph.loop_config,
        "graph": graph,
    }
