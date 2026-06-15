"""Agreement Analysis agent graph — intake → extract → human review → audit."""

from engine.graph import Constraint, EdgeCondition, EdgeSpec, Goal, SuccessCriterion
from engine.graph.edge import GraphSpec

from .config import metadata
from .nodes import audit_node, extract_node, human_review_node, intake_node

goal = Goal(
    id="agreement-analysis",
    name="Agreement Analysis",
    description="Extract agreement terms with human approval and audit trail.",
    success_criteria=[
        SuccessCriterion(
            id="sc-fields",
            description="Key agreement fields extracted",
            metric="fields_extracted",
            target="true",
            weight=0.35,
        ),
        SuccessCriterion(
            id="sc-review",
            description="Human reviewer approved or edited output",
            metric="human_review_complete",
            target="true",
            weight=0.35,
        ),
        SuccessCriterion(
            id="sc-audit",
            description="Audit record produced",
            metric="audit_record_present",
            target="true",
            weight=0.3,
        ),
    ],
    constraints=[
        Constraint(
            id="c-no-fabrication",
            description="Do not add agreement terms not present in source text",
            constraint_type="hard",
            category="quality",
        ),
    ],
)

nodes = [intake_node, extract_node, human_review_node, audit_node]

edges = [
    EdgeSpec(
        id="intake-to-extract",
        source="intake",
        target="extract",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="extract-to-review",
        source="extract",
        target="human_review",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="review-to-audit",
        source="human_review",
        target="audit",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]

entry_node = "intake"
entry_points = {"start": "intake"}
pause_nodes = ["human_review"]
terminal_nodes = ["audit"]
loop_config = {
    "max_iterations": 50,
    "max_tool_calls_per_turn": 10,
    "max_history_tokens": 64000,
}

graph = GraphSpec(
    id="agreement-analysis-graph",
    goal_id=goal.id,
    version=metadata.version,
    entry_node=entry_node,
    entry_points=entry_points,
    terminal_nodes=terminal_nodes,
    pause_nodes=pause_nodes,
    nodes=nodes,
    edges=edges,
    loop_config=loop_config,
)
