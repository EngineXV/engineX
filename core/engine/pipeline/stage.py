"""Pipeline stage base class and request/response types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal


class PipelineRejectedError(Exception):
    """Raised when a middleware stage rejects a trigger request."""

    def __init__(self, stage_name: str, reason: str) -> None:
        super().__init__(f"Pipeline rejected by {stage_name}: {reason}")
        self.stage_name = stage_name
        self.reason = reason


@dataclass
class PipelineContext:
    """Carries trigger request data through middleware stages."""

    entry_point_id: str
    input_data: dict[str, Any]
    correlation_id: str | None = None
    session_state: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Outcome of a stage ``process`` call."""

    action: Literal["continue", "reject", "transform"] = "continue"
    input_data: dict[str, Any] | None = None
    rejection_reason: str | None = None


class PipelineStage(ABC):
    """Base class for runtime trigger middleware."""

    order: int = 100

    async def initialize(self) -> None:
        """Called once when the runtime starts."""
        return None

    @abstractmethod
    async def process(self, ctx: PipelineContext) -> PipelineResult:
        """Inspect or transform an incoming trigger request."""

    async def post_process(self, ctx: PipelineContext, result: Any) -> Any:
        """Optional post-execution hook. Default: pass-through."""
        return result
