"""Support Triage agent graph."""

from engine.graph import EdgeCondition, EdgeSpec, Goal, SuccessCriterion
from engine.graph.edge import GraphSpec

from .config import metadata
from .nodes import classify_node, finalize_node, intake_node, review_node

goal = Goal(
    id="support-triage",
    name="Support Triage",
    description="Classify support requests and draft replies with human approval.",
    success_criteria=[
        SuccessCriterion(
            id="sc-approved",
            description="Human approved draft reply",
            metric="approved",
            target="true",
            weight=1.0,
        )
    ],
)

nodes = [intake_node, classify_node, review_node, finalize_node]
edges = [
    EdgeSpec(id="e1", source="intake", target="classify", condition=EdgeCondition.ON_SUCCESS, priority=1),
    EdgeSpec(id="e2", source="classify", target="review", condition=EdgeCondition.ON_SUCCESS, priority=1),
    EdgeSpec(id="e3", source="review", target="finalize", condition=EdgeCondition.ON_SUCCESS, priority=1),
]

graph = GraphSpec(
    id="support-triage-graph",
    goal_id=goal.id,
    version=metadata.version,
    entry_node="intake",
    entry_points={"start": "intake"},
    pause_nodes=["review"],
    terminal_nodes=["finalize"],
    nodes=nodes,
    edges=edges,
)
