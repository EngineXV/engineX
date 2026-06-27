"""Input validation middleware for entry-point triggers."""

from __future__ import annotations

from engine.pipeline.registry import register
from engine.pipeline.stage import PipelineContext, PipelineResult, PipelineStage


@register("input_validation")
class InputValidationStage(PipelineStage):
    """Validate ``input_data`` against per-entry-point schemas."""

    order = 100

    def __init__(self, schemas: dict[str, dict[str, type]] | None = None) -> None:
        self._schemas = schemas or {}

    async def process(self, ctx: PipelineContext) -> PipelineResult:
        schema = self._schemas.get(ctx.entry_point_id)
        if not schema:
            return PipelineResult(action="continue")

        for key, expected_type in schema.items():
            if key not in ctx.input_data:
                return PipelineResult(
                    action="reject",
                    rejection_reason=f"Missing required input key: '{key}'",
                )
            value = ctx.input_data[key]
            if not isinstance(value, expected_type):
                return PipelineResult(
                    action="reject",
                    rejection_reason=(
                        f"Input key '{key}' has type {type(value).__name__}, "
                        f"expected {expected_type.__name__}"
                    ),
                )
        return PipelineResult(action="continue")
