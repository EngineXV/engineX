"""Judge protocol and escalation helpers for event-loop nodes"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Literal, Protocol, runtime_checkable


class _EscalationReceiver:
    """Temporary receiver registered in node_registry"""

    def __init__(self) -> None:
        self._event = asyncio.Event()
        self._response: str | None = None

    async def inject_event(self, content: str, *, is_client_input: bool = False) -> None:
        """Called by ExecutionStream.inject_input() when the user responds"""
        self._response = content
        self._event.set()

    async def wait(self) -> str | None:
        """Block until inject_event() delivers the user's response"""
        await self._event.wait()
        return self._response


class TurnCancelled(Exception):
    """Raised when a turn is cancelled mid-stream"""


@dataclass
class JudgeVerdict:
    """Result of judge evaluation for the event loop"""

    action: Literal["ACCEPT", "RETRY", "ESCALATE"]
    feedback: str = ""


@runtime_checkable
class JudgeProtocol(Protocol):
    """Protocol for event-loop judges"""

    async def evaluate(self, context: dict[str, Any]) -> JudgeVerdict: ...


class SubagentJudge:
    """Judge for subagent execution"""

    def __init__(self, task: str, max_iterations: int = 10):
        self._task = task
        self._max_iterations = max_iterations

    async def evaluate(self, context: dict[str, Any]) -> JudgeVerdict:
        missing = context.get("missing_keys", [])
        if not missing:
            return JudgeVerdict(action="ACCEPT")

        iteration = context.get("iteration", 0)
        remaining = self._max_iterations - iteration - 1

        if remaining <= 3:
            urgency = (
                f"URGENT: Only {remaining} iterations left. "
                f"Stop all other work and call set_output NOW for: {missing}"
            )
        elif remaining <= self._max_iterations // 2:
            urgency = (
                f"WARNING: {remaining} iterations remaining. "
                f"You must call set_output for: {missing}"
            )
        else:
            urgency = f"Still missing required outputs: {missing}"

        return JudgeVerdict(action="RETRY", feedback=urgency)
