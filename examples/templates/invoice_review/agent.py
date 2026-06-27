"""Invoice Review agent graph."""

from engine.graph import EdgeCondition, EdgeSpec, Goal, SuccessCriterion
from engine.graph.edge import GraphSpec

from .config import metadata
from .nodes import approval_node, audit_node, extract_node, intake_node

goal = Goal(
    id="invoice-review",
    name="Invoice Review",
    description="Extract invoice data and obtain finance approval.",
    success_criteria=[
        SuccessCriterion(
            id="sc-audit",
            description="Audit record created",
            metric="audit_record_present",
            target="true",
            weight=1.0,
        )
    ],
)

nodes = [intake_node, extract_node, approval_node, audit_node]
edges = [
    EdgeSpec(id="e1", source="intake", target="extract", condition=EdgeCondition.ON_SUCCESS, priority=1),
    EdgeSpec(id="e2", source="extract", target="approval", condition=EdgeCondition.ON_SUCCESS, priority=1),
    EdgeSpec(id="e3", source="approval", target="audit", condition=EdgeCondition.ON_SUCCESS, priority=1),
]

graph = GraphSpec(
    id="invoice-review-graph",
    goal_id=goal.id,
    version=metadata.version,
    entry_node="intake",
    entry_points={"start": "intake"},
    pause_nodes=["approval"],
    terminal_nodes=["audit"],
    nodes=nodes,
    edges=edges,
)
