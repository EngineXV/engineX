"""Helpers for recording graph routing decisions during execution."""

from __future__ import annotations

import logging
from typing import Any, Protocol

from engine.schemas.decision import DecisionType

logger = logging.getLogger(__name__)


class DecisionRuntime(Protocol):
    """Minimal runtime surface used for execution tracking."""

    def set_node(self, node_id: str) -> None: ...

    def decide(
        self,
        intent: str,
        options: list[dict[str, Any]],
        chosen: str,
        reasoning: str,
        node_id: str | None = None,
        decision_type: DecisionType = DecisionType.CUSTOM,
        constraints: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> str: ...

    def record_outcome(
        self,
        decision_id: str,
        success: bool,
        result: Any = None,
        error: str | None = None,
        summary: str = "",
        state_changes: dict[str, Any] | None = None,
        tokens_used: int = 0,
        latency_ms: int = 0,
    ) -> None: ...


def record_edge_route(
    runtime: DecisionRuntime,
    *,
    source_node_id: str,
    target_node_id: str,
    edge_condition: str,
    reasoning: str = "",
) -> None:
    """Record a path-choice decision when the executor follows an edge."""
    try:
        runtime.set_node(source_node_id)
        decision_id = runtime.decide(
            intent=f"Route from '{source_node_id}' to '{target_node_id}'",
            options=[
                {
                    "id": target_node_id,
                    "description": f"Follow edge to {target_node_id}",
                    "action_type": "route",
                },
                {
                    "id": "stop",
                    "description": "End execution",
                    "action_type": "terminate",
                },
            ],
            chosen=target_node_id,
            reasoning=reasoning or f"Edge condition '{edge_condition}' matched",
            node_id=source_node_id,
            decision_type=DecisionType.PATH_CHOICE,
            context={"edge_condition": edge_condition},
        )
        if decision_id:
            runtime.record_outcome(
                decision_id=decision_id,
                success=True,
                summary=f"Routed to {target_node_id}",
            )
    except Exception:
        logger.debug("Edge route tracking skipped", exc_info=True)
