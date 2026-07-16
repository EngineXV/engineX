"""Cost guard stage — reject requests over a pre-flight budget."""

from __future__ import annotations

from engine.config import get_engine_config
from engine.pipeline.registry import register
from engine.pipeline.stage import PipelineContext, PipelineResult, PipelineStage


@register("cost_guard")
class CostGuardStage(PipelineStage):
    """Reject requests whose estimated cost exceeds the per-request budget."""

    order = 300

    def __init__(self, max_cost_per_request: float | None = None) -> None:
        if max_cost_per_request is not None:
            self._budget = float(max_cost_per_request)
        else:
            cost_guard = get_engine_config().get("pipeline", {}).get("cost_guard", {})
            self._budget = float(cost_guard.get("max_cost_per_request", 1.0))

    async def process(self, ctx: PipelineContext) -> PipelineResult:
        estimated = ctx.metadata.get("estimated_cost")
        if estimated is None:
            return PipelineResult(action="continue")
        if estimated > self._budget:
            return PipelineResult(
                action="reject",
                rejection_reason=(
                    f"Estimated cost ${estimated:.4f} exceeds budget ${self._budget:.4f}"
                ),
            )
        return PipelineResult(action="continue")
