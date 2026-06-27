"""Task list id helpers."""

from __future__ import annotations


def session_task_list_id(agent_id: str, session_id: str) -> str:
    return f"session:{agent_id}:{session_id}"


def template_task_list_id(template_id: str) -> str:
    return f"template:{template_id}"


def supervisor_session_task_list_id(session_id: str) -> str:
    """Dashboard supervisor session action plan scope."""
    return f"supervisor:{session_id}"
