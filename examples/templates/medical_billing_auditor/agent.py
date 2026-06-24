"""Medical Billing Auditor agent graph — intake → extraction → validation → HITL → resolution → audit."""

from engine.graph import Constraint, EdgeCondition, EdgeSpec, Goal, SuccessCriterion
from engine.graph.edge import GraphSpec

from .config import metadata
from .nodes import (
    audit_storage,
    code_extraction,
    compliance_validation,
    ehr_intake,
    hitl_review,
    resolution_handshake,
)

goal = Goal(
    id="medical-billing-auditor",
    name="Medical Billing & Insurance Coding Auditor",
    description="HITL workflow: ingest clinical EHR → extract codes → compliance validation → human approval → audit trail",
    success_criteria=[
        SuccessCriterion(
            id="sc-extraction",
            description="Clinical procedures extracted and mapped to billing codes",
            metric="codes_extracted",
            target="true",
            weight=0.25,
        ),
        SuccessCriterion(
            id="sc-validation",
            description="Codes pass compliance validation against carrier rules",
            metric="codes_validated",
            target="true",
            weight=0.25,
        ),
        SuccessCriterion(
            id="sc-hitl",
            description="High-risk items correctly escalated for human review",
            metric="human_review_escalation",
            target="true",
            weight=0.25,
        ),
        SuccessCriterion(
            id="sc-audit",
            description="Final claim state and override logs persisted to audit storage",
            metric="audit_trail_complete",
            target="true",
            weight=0.25,
        ),
    ],
    constraints=[
        Constraint(
            id="c-no-claim-denial",
            description="Prevent claim denials due to coding errors; ensure compliance with carrier rules",
            constraint_type="hard",
            category="compliance",
        ),
        Constraint(
            id="c-audit-trail",
            description="Maintain complete, auditable trail of all human approvals and code modifications",
            constraint_type="hard",
            category="governance",
        ),
        Constraint(
            id="c-human-safety-net",
            description="Halt execution and require explicit human authorization before finalizing high-risk claims",
            constraint_type="hard",
            category="safety",
        ),
    ],
)

nodes = [
    ehr_intake,
    code_extraction,
    compliance_validation,
    hitl_review,
    resolution_handshake,
    audit_storage,
]

edges = [
    EdgeSpec(
        id="intake-to-extraction",
        source="ehr_intake",
        target="code_extraction",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="extraction-to-validation",
        source="code_extraction",
        target="compliance_validation",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="validation-to-hitl",
        source="compliance_validation",
        target="hitl_review",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="hitl-to-resolution",
        source="hitl_review",
        target="resolution_handshake",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="resolution-to-audit",
        source="resolution_handshake",
        target="audit_storage",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]

entry_node = "ehr_intake"
entry_points = {"start": "ehr_intake"}
pause_nodes = ["hitl_review"]
terminal_nodes = ["audit_storage"]
loop_config = {
    "max_iterations": 50,
    "max_tool_calls_per_turn": 10,
    "max_history_tokens": 64000,
}

graph = GraphSpec(
    id="medical-billing-auditor-graph",
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

__all__ = ["goal", "nodes", "edges", "graph"]
