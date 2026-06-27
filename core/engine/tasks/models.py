"""Task tracker data models."""

from __future__ import annotations

import time
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskListRole(StrEnum):
    SESSION = "session"
    TEMPLATE = "template"


class TaskRecord(BaseModel):
    """One tracked unit of work for a session."""

    id: int
    subject: str
    description: str = ""
    active_form: str | None = None
    owner: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    blocks: list[int] = Field(default_factory=list)
    blocked_by: list[int] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class TaskListMeta(BaseModel):
    task_list_id: str
    role: TaskListRole
    creator_agent_id: str | None = None
    created_at: float = Field(default_factory=time.time)
    schema_version: int = 1


class TaskListDocument(BaseModel):
    meta: TaskListMeta
    highwatermark: int = 0
    tasks: list[TaskRecord] = Field(default_factory=list)
