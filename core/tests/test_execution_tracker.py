"""Tests for graph execution decision tracking."""

from __future__ import annotations

from engine.schemas.decision import DecisionType
from engine.tracker.execution_tracker import record_edge_route


class _FakeRuntime:
    def __init__(self) -> None:
        self.node_id: str | None = None
        self.decisions: list[dict] = []
        self.outcomes: list[dict] = []

    def set_node(self, node_id: str) -> None:
        self.node_id = node_id

    def decide(
        self,
        intent: str,
        options: list[dict],
        chosen: str,
        reasoning: str,
        node_id: str | None = None,
        decision_type: DecisionType = DecisionType.CUSTOM,
        constraints: list[str] | None = None,
        context: dict | None = None,
    ) -> str:
        decision_id = f"dec_{len(self.decisions)}"
        self.decisions.append(
            {
                "id": decision_id,
                "intent": intent,
                "chosen": chosen,
                "node_id": node_id,
                "decision_type": decision_type,
            }
        )
        return decision_id

    def record_outcome(self, decision_id: str, success: bool, summary: str = "", **kwargs) -> None:
        self.outcomes.append(
            {"decision_id": decision_id, "success": success, "summary": summary}
        )


def test_record_edge_route_creates_path_choice() -> None:
    runtime = _FakeRuntime()
    record_edge_route(
        runtime,
        source_node_id="extract",
        target_node_id="review",
        edge_condition="on_success",
        reasoning="Node completed successfully",
    )
    assert len(runtime.decisions) == 1
    assert runtime.decisions[0]["decision_type"] == DecisionType.PATH_CHOICE
    assert runtime.decisions[0]["chosen"] == "review"
    assert len(runtime.outcomes) == 1
    assert runtime.outcomes[0]["success"] is True
