"""Default action-plan templates for department supervisors."""

from __future__ import annotations

from typing import Any

DEFAULT_SUPERVISOR_PLAN: list[dict[str, Any]] = [
    {
        "subject": "Understand operator request",
        "description": "Clarify goals, constraints, and any pasted source material.",
        "active_form": "Reviewing operator request",
    },
    {
        "subject": "Spawn worker on delegated task",
        "description": "Use spawn_worker with the operator's content.",
        "active_form": "Starting worker agent",
    },
    {
        "subject": "Monitor worker progress",
        "description": "Check status and relay HITL prompts to the operator.",
        "active_form": "Monitoring worker execution",
    },
    {
        "subject": "Confirm completion with operator",
        "description": "Summarize outcomes and next steps.",
        "active_form": "Closing out session",
    },
]

DEPARTMENT_PLANS: dict[str, list[dict[str, Any]]] = {
    "Technology": [
        {
            "subject": "Assess technical scope",
            "description": "Identify systems, APIs, and constraints mentioned by the operator.",
            "active_form": "Scoping technical work",
        },
        {
            "subject": "Delegate analysis to worker",
            "description": "Spawn worker with agreement or technical artifact text.",
            "active_form": "Delegating to worker",
        },
        {
            "subject": "Track worker HITL checkpoints",
            "description": "Surface review gates and operator approvals.",
            "active_form": "Monitoring worker checkpoints",
        },
    ],
    "Legal": [
        {
            "subject": "Capture legal context",
            "description": "Note jurisdiction, parties, and review objectives.",
            "active_form": "Gathering legal context",
        },
        {
            "subject": "Run agreement analysis worker",
            "description": "Spawn worker with contract text — do not extract terms yourself.",
            "active_form": "Running agreement worker",
        },
        {
            "subject": "Escalate human review items",
            "description": "Route approval/edits to the operator promptly.",
            "active_form": "Managing human review",
        },
    ],
    "Finance": DEFAULT_SUPERVISOR_PLAN,
    "Marketing": DEFAULT_SUPERVISOR_PLAN,
    "Growth": DEFAULT_SUPERVISOR_PLAN,
    "Operations": DEFAULT_SUPERVISOR_PLAN,
    "Brand & Design": DEFAULT_SUPERVISOR_PLAN,
}


def plan_for_department(department: str | None) -> list[dict[str, Any]]:
    if not department:
        return [dict(item) for item in DEFAULT_SUPERVISOR_PLAN]
    plan = DEPARTMENT_PLANS.get(department)
    if plan is None:
        return [dict(item) for item in DEFAULT_SUPERVISOR_PLAN]
    return [dict(item) for item in plan]
