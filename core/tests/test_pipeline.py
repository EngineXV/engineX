"""Tests for runtime trigger middleware pipeline."""

from __future__ import annotations

import pytest

from engine.pipeline.registry import build_pipeline_from_config
from engine.pipeline.stage import PipelineContext, PipelineRejectedError, PipelineStage


class _RejectStage(PipelineStage):
    order = 300

    async def process(self, ctx: PipelineContext):
        from engine.pipeline.stage import PipelineResult

        return PipelineResult(action="reject", rejection_reason="blocked")


@pytest.mark.asyncio
async def test_rate_limit_stage_allows_under_limit() -> None:
    pipeline = build_pipeline_from_config(
        [{"type": "rate_limit", "config": {"max_requests_per_minute": 2}}]
    )
    ctx = PipelineContext(entry_point_id="manual", input_data={"x": 1})
    result = await pipeline.run(ctx)
    assert result.input_data == {"x": 1}


@pytest.mark.asyncio
async def test_rate_limit_stage_rejects_over_limit() -> None:
    pipeline = build_pipeline_from_config(
        [{"type": "rate_limit", "config": {"max_requests_per_minute": 1}}]
    )
    ctx = PipelineContext(entry_point_id="manual", input_data={})
    await pipeline.run(ctx)
    with pytest.raises(PipelineRejectedError):
        await pipeline.run(ctx)


@pytest.mark.asyncio
async def test_input_validation_stage_rejects_missing_key() -> None:
    pipeline = build_pipeline_from_config(
        [
            {
                "type": "input_validation",
                "config": {"schemas": {"manual": {"topic": str}}},
            }
        ]
    )
    ctx = PipelineContext(entry_point_id="manual", input_data={})
    with pytest.raises(PipelineRejectedError, match="Missing required input key"):
        await pipeline.run(ctx)


@pytest.mark.asyncio
async def test_cost_guard_stage_rejects_over_budget() -> None:
    pipeline = build_pipeline_from_config(
        [{"type": "cost_guard", "config": {"max_cost_per_request": 0.25}}]
    )
    ctx = PipelineContext(
        entry_point_id="manual",
        input_data={},
        metadata={"estimated_cost": 0.50},
    )
    with pytest.raises(PipelineRejectedError, match="Estimated cost"):
        await pipeline.run(ctx)


@pytest.mark.asyncio
async def test_pipeline_runs_stages_in_order() -> None:
    seen: list[str] = []

    class _FirstStage(PipelineStage):
        order = 100

        async def process(self, ctx: PipelineContext):
            from engine.pipeline.stage import PipelineResult

            seen.append("first")
            return PipelineResult(action="continue")

    class _SecondStage(PipelineStage):
        order = 200

        async def process(self, ctx: PipelineContext):
            from engine.pipeline.stage import PipelineResult

            seen.append("second")
            return PipelineResult(action="continue")

    from engine.pipeline.runner import PipelineRunner

    pipeline = PipelineRunner([_SecondStage(), _FirstStage(), _RejectStage()])
    ctx = PipelineContext(entry_point_id="manual", input_data={})
    with pytest.raises(PipelineRejectedError):
        await pipeline.run(ctx)
    assert seen == ["first", "second"]
