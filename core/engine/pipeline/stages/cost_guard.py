"""Cost guard stage — reject requests over a pre-flight budget."""

from __future__ import annotations

import logging

from engine.config import get_engine_config
from engine.pipeline.registry import register
from engine.pipeline.stage import PipelineContext, PipelineResult, PipelineStage


logger = logging.getLogger(__name__)


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
        execution = get_engine_config().get("execution", {})
        self._run_budget = float(execution.get("cost_budget") or 0.0) or None

    async def process(self, ctx: PipelineContext) -> PipelineResult:
        estimated = ctx.metadata.get("estimated_cost")
        if estimated is None:
            estimated = ctx.metadata.get("estimated_cost_usd")
        run_estimated = None
        if ctx.session_state:
            metrics = ctx.session_state.get("metrics")
            if isinstance(metrics, dict):
                run_estimated = metrics.get("estimated_cost_usd")
        if estimated is not None and estimated > self._budget:
            logger.warning(
                "Rejecting request cost %.4f over per-request budget %.4f",
                estimated,
                self._budget,
            )
            return PipelineResult(
                action="reject",
                rejection_reason=(
                    f"Estimated cost ${estimated:.4f} exceeds budget ${self._budget:.4f}"
                ),
            )
        if self._run_budget is not None and run_estimated is not None and run_estimated > self._run_budget:
            logger.warning(
                "Rejecting run cost %.4f over run budget %.4f",
                run_estimated,
                self._run_budget,
            )
            return PipelineResult(
                action="reject",
                rejection_reason=(
                    f"Run cost ${run_estimated:.4f} exceeds budget ${self._run_budget:.4f}"
                ),
            )
        return PipelineResult(action="continue")
