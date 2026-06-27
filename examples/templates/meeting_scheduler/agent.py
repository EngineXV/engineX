"""Meeting Scheduler agent graph — intake → schedule → confirm (loop)."""

from engine.graph import Constraint, EdgeCondition, EdgeSpec, Goal, SuccessCriterion
from engine.graph.edge import GraphSpec

from .config import metadata
from .nodes import confirm_node, intake_node, schedule_node

goal = Goal(
    id="meeting-scheduler-goal",
    name="Schedule Meetings",
    description="Check calendar availability, find optimal meeting times, record meetings, and send reminders.",
    success_criteria=[
        SuccessCriterion(
            id="sc-1",
            description="Meeting time found within requested duration",
            metric="calendar_availability",
            target="success",
            weight=0.35,
        ),
        SuccessCriterion(
            id="sc-2",
            description="Meeting recorded in spreadsheet accurately",
            metric="data_persistence",
            target="recorded",
            weight=0.30,
        ),
        SuccessCriterion(
            id="sc-3",
            description="Attendee email reminder sent",
            metric="communication",
            target="sent",
            weight=0.25,
        ),
        SuccessCriterion(
            id="sc-4",
            description="User confirms meeting details",
            metric="user_acknowledgment",
            target="confirmed",
            weight=0.10,
        ),
    ],
    constraints=[
        Constraint(
            id="c-1",
            description="Must use Google Calendar API for availability check",
            constraint_type="hard",
            category="functional",
        ),
        Constraint(
            id="c-2",
            description="Meeting duration must match requested time",
            constraint_type="hard",
            category="accuracy",
        ),
        Constraint(
            id="c-3",
            description="Spreadsheet record must include date, time, attendee, title",
            constraint_type="hard",
            category="quality",
        ),
    ],
)

nodes = [intake_node, schedule_node, confirm_node]

edges = [
    EdgeSpec(
        id="intake-to-schedule",
        source="intake",
        target="schedule",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="schedule-to-confirm",
        source="schedule",
        target="confirm",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="confirm-to-intake",
        source="confirm",
        target="intake",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="str(next_action).lower() == 'another'",
        priority=1,
    ),
]

entry_node = "intake"
entry_points = {"start": "intake"}
pause_nodes = []
terminal_nodes = []

conversation_mode = "continuous"
identity_prompt = (
    "You are a helpful meeting scheduler assistant that manages calendar availability and sends confirmations."
)
loop_config = {
    "max_iterations": 100,
    "max_tool_calls_per_turn": 20,
    "max_history_tokens": 32000,
}

graph = GraphSpec(
    id="meeting-scheduler-graph",
    goal_id=goal.id,
    version=metadata.version,
    entry_node=entry_node,
    entry_points=entry_points,
    terminal_nodes=terminal_nodes,
    pause_nodes=pause_nodes,
    nodes=nodes,
    edges=edges,
    loop_config=loop_config,
    conversation_mode=conversation_mode,
    identity_prompt=identity_prompt,
)
