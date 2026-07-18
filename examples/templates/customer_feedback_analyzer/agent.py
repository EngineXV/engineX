"""Customer Feedback Analyzer agent — intake → analysis → draft → human review."""

from engine.graph import Constraint, EdgeCondition, EdgeSpec, Goal, SuccessCriterion
from engine.graph.edge import GraphSpec

from .config import metadata
from .nodes import analysis_node, drafting_node, intake_node, review_node

goal = Goal(
    id="customer-feedback",
    name="Customer Feedback Analyzer",
    description=(
        "Analyze customer feedback to determine sentiment, categorize the issue, "
        "and draft a professional response for human review."
    ),
    success_criteria=[
        SuccessCriterion(
            id="categorization",
            description="Accurately categorize the feedback issue type.",
            metric="category_assigned",
            target="true",
            weight=0.33,
        ),
        SuccessCriterion(
            id="draft-response",
            description="Draft a professional response based on the analysis.",
            metric="response_drafted",
            target="true",
            weight=0.33,
        ),
        SuccessCriterion(
            id="human-review",
            description="Human reviewer approves the final drafted message.",
            metric="approval_status",
            target="approved",
            weight=0.34,
        ),
    ],
    constraints=[
        Constraint(
            id="professional-tone",
            description="The drafted response must always maintain a professional and empathetic tone.",
            constraint_type="hard",
            category="tone",
        ),
        Constraint(
            id="human-checkpoint",
            description="Do not finalize or 'send' the response without explicit human approval.",
            constraint_type="hard",
            category="interaction",
        ),
    ],
)

nodes = [intake_node, analysis_node, drafting_node, review_node]

edges = [
    EdgeSpec(
        id="intake-to-analysis",
        source="intake",
        target="analysis",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="analysis-to-drafting",
        source="analysis",
        target="drafting",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="drafting-to-review",
        source="drafting",
        target="review",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="review-to-drafting",
        source="review",
        target="drafting",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="str(final_action).lower() == 'needs_revision'",
        priority=2,
    ),
    # In a real app, this would go to a "send_email" node, but we'll terminate here
    # when approved since it's a demonstration.
]

entry_node = "intake"
entry_points = {"start": "intake"}
pause_nodes = ["review"]
terminal_nodes = ["review"] # Terminates after review if approved

loop_config = {
    "max_iterations": 20,
    "max_tool_calls_per_turn": 10,
    "max_history_tokens": 16000,
}

graph = GraphSpec(
    id="customer-feedback-graph",
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
