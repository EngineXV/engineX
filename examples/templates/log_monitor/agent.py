"""Log monitor agent — Grafana polling, dedup, LLM triage, alerts, human review."""

from engine.graph import Constraint, EdgeCondition, EdgeSpec, Goal, SuccessCriterion
from engine.graph.edge import AsyncEntryPointSpec, GraphSpec

from .config import metadata
from .nodes import (
    dispatch_node,
    fetch_enrich_node,
    human_review_node,
    learn_node,
    llm_triage_node,
)

goal = Goal(
    id="log-monitor",
    name="Log Monitor",
    description="Monitor Grafana errors, deduplicate, score, triage, and alert with human review.",
    success_criteria=[
        SuccessCriterion(
            id="sc-poll",
            description="Logs fetched and scored each tick",
            metric="tick_completed",
            target="true",
            weight=0.25,
        ),
        SuccessCriterion(
            id="sc-dedup",
            description="Duplicate fingerprints skipped within mute window",
            metric="dedup_active",
            target="true",
            weight=0.25,
        ),
        SuccessCriterion(
            id="sc-alert",
            description="SEVERE/HIGH incidents routed to alert channels",
            metric="alerts_dispatched",
            target="true",
            weight=0.25,
        ),
        SuccessCriterion(
            id="sc-learn",
            description="Outcomes recorded for tuning",
            metric="learning_recorded",
            target="true",
            weight=0.25,
        ),
    ],
    constraints=[
        Constraint(
            id="c-no-spam",
            description="Do not re-alert muted fingerprints within mute window",
            constraint_type="hard",
            category="operational",
        ),
        Constraint(
            id="c-filtered-logs",
            description="Only process Grafana logs pre-filtered by error keywords",
            constraint_type="hard",
            category="quality",
        ),
    ],
)

nodes = [
    fetch_enrich_node,
    llm_triage_node,
    dispatch_node,
    human_review_node,
    learn_node,
]

edges = [
    EdgeSpec(
        id="fetch-to-triage",
        source="fetch_enrich",
        target="llm_triage",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="needs_llm_triage == True",
        priority=2,
    ),
    EdgeSpec(
        id="fetch-to-dispatch",
        source="fetch_enrich",
        target="dispatch",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="needs_llm_triage != True",
        priority=1,
    ),
    EdgeSpec(
        id="triage-to-dispatch",
        source="llm_triage",
        target="dispatch",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="dispatch-to-human",
        source="dispatch",
        target="human_review",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="needs_human_review == True",
        priority=2,
    ),
    EdgeSpec(
        id="dispatch-to-learn",
        source="dispatch",
        target="learn",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="needs_human_review != True",
        priority=1,
    ),
    EdgeSpec(
        id="human-to-learn",
        source="human_review",
        target="learn",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]

entry_node = "fetch_enrich"
entry_points = {"start": "fetch_enrich"}
pause_nodes = ["human_review"]
terminal_nodes = ["learn"]

async_entry_points = [
    AsyncEntryPointSpec(
        id="monitor-timer",
        name="Monitor Timer",
        entry_node="fetch_enrich",
        trigger_type="timer",
        trigger_config={
            "interval_minutes": 1,
            "run_immediately": True,
        },
        isolation_level="shared",
        max_concurrent=1,
    ),
]

loop_config = {
    "max_iterations": 30,
    "max_tool_calls_per_turn": 15,
    "max_history_tokens": 48000,
}

graph = GraphSpec(
    id="log-monitor-graph",
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


# Stub for compatibility
skip_credential_validation = False
