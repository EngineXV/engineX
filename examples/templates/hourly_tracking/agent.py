"""Hourly Tracking Agent."""

from engine.graph import Constraint, EdgeCondition, EdgeSpec, Goal, SuccessCriterion
from engine.graph.edge import AsyncEntryPointSpec, GraphSpec

from .config import metadata
from .nodes import (
    fetch_transactions_node,
    process_transactions_node,
    validate_transactions_node,
    correct_transactions_node,
    human_review_node,
    store_results_node,
)

goal = Goal(
    id="hourly-tracking",
    name="Hourly Tracking Agent",
    description="Hourly reconciliation of broker and investor transactions.",
    success_criteria=[
        SuccessCriterion(
            id="tracking-complete",
            description="Transactions validated and stored",
            metric="tracking_complete",
            target="true",
            weight=1.0,
        ),
    ],
    constraints=[
        Constraint(
            id="financial-balance",
            description="Inputs must equal outputs plus fees",
            constraint_type="hard",
            category="financial",
        ),
    ],
)

nodes = [
    fetch_transactions_node,
    process_transactions_node,
    validate_transactions_node,
    correct_transactions_node,
    human_review_node,
    store_results_node,
]

edges = [
    EdgeSpec(
        id="fetch-to-process",
        source="fetch_transactions",
        target="process_transactions",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="process-to-validate",
        source="process_transactions",
        target="validate_transactions",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="validate-to-store",
        source="validate_transactions",
        target="store_results",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="validation_passed == True",
        priority=3,
    ),
    EdgeSpec(
        id="validate-to-human",
        source="validate_transactions",
        target="human_review",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="requires_human_review == True",
        priority=2,
    ),
    EdgeSpec(
        id="validate-to-correct",
        source="validate_transactions",
        target="correct_transactions",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="validation_passed == False and requires_human_review != True",
        priority=1,
    ),
    EdgeSpec(
        id="correct-to-validate",
        source="correct_transactions",
        target="validate_transactions",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="human-to-store",
        source="human_review",
        target="store_results",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="human_approved == True",
        priority=2,
    ),
    EdgeSpec(
        id="human-to-correct",
        source="human_review",
        target="correct_transactions",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="human_approved == False",
        priority=1,
    ),
]

entry_node = "fetch_transactions"

entry_points = {"start": "fetch_transactions"}

pause_nodes = ["human_review"]

terminal_nodes = ["store_results"]

async_entry_points = [
    AsyncEntryPointSpec(
        id="hourly-tracker",
        name="Hourly Tracker",
        entry_node="fetch_transactions",
        trigger_type="timer",
        trigger_config={
            "interval_minutes": 60,
            "run_immediately": True,
        },
        isolation_level="shared",
        max_concurrent=1,
    ),
]

loop_config = {
    "max_iterations": 20,
    "max_tool_calls_per_turn": 10,
    "max_history_tokens": 24000,
}

graph = GraphSpec(
    id="hourly-tracking-graph",
    goal_id=goal.id,
    version=metadata.version,
    entry_node=entry_node,
    entry_points=entry_points,
    async_entry_points=async_entry_points,
    terminal_nodes=terminal_nodes,
    pause_nodes=pause_nodes,
    nodes=nodes,
    edges=edges,
    loop_config=loop_config,
)
