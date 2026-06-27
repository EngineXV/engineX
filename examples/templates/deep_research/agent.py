"""Deep Research agent — intake → research → review → report with feedback loops."""

from engine.graph import Constraint, EdgeCondition, EdgeSpec, Goal, SuccessCriterion
from engine.graph.edge import GraphSpec

from .config import metadata
from .nodes import intake_node, report_node, research_node, review_node

goal = Goal(
    id="deep-research",
    name="Deep Research",
    description=(
        "Research any topic via multi-source search and synthesis, "
        "with human review before the final cited report."
    ),
    success_criteria=[
        SuccessCriterion(
            id="source-diversity",
            description="Use multiple diverse sources",
            metric="source_count",
            target=">=3",
            weight=0.25,
        ),
        SuccessCriterion(
            id="citation-coverage",
            description="Report cites sources for factual claims",
            metric="citation_coverage",
            target="high",
            weight=0.25,
        ),
        SuccessCriterion(
            id="user-review",
            description="User reviewed findings before report",
            metric="user_review_complete",
            target="true",
            weight=0.25,
        ),
        SuccessCriterion(
            id="report-delivered",
            description="HTML report delivered to user",
            metric="delivery_status",
            target="completed",
            weight=0.25,
        ),
    ],
    constraints=[
        Constraint(
            id="no-hallucination",
            description="Only include information found in fetched sources",
            constraint_type="hard",
            category="accuracy",
        ),
        Constraint(
            id="user-checkpoint",
            description="Present findings for human review before final report",
            constraint_type="hard",
            category="interaction",
        ),
    ],
)

nodes = [intake_node, research_node, review_node, report_node]

edges = [
    EdgeSpec(
        id="intake-to-research",
        source="intake",
        target="research",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="research-to-review",
        source="research",
        target="review",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="review-to-research",
        source="review",
        target="research",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="needs_more_research == True",
        priority=1,
    ),
    EdgeSpec(
        id="review-to-report",
        source="review",
        target="report",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="needs_more_research == False",
        priority=2,
    ),
    EdgeSpec(
        id="report-to-research",
        source="report",
        target="research",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="str(next_action).lower() == 'more_research'",
        priority=2,
    ),
    EdgeSpec(
        id="report-to-intake",
        source="report",
        target="intake",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="str(next_action).lower() != 'more_research'",
        priority=1,
    ),
]

entry_node = "intake"
entry_points = {"start": "intake"}
pause_nodes = ["review", "report"]
terminal_nodes = []

loop_config = {
    "max_iterations": 100,
    "max_tool_calls_per_turn": 30,
    "max_history_tokens": 48000,
}

graph = GraphSpec(
    id="deep-research-graph",
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
