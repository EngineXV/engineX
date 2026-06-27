"""Pipeline stage registry and config-driven construction."""

from __future__ import annotations

import logging
from typing import Any

from engine.pipeline.runner import PipelineRunner
from engine.pipeline.stage import PipelineStage

logger = logging.getLogger(__name__)

_STAGE_REGISTRY: dict[str, type[PipelineStage]] = {}


def register(name: str):
    """Decorator to register a pipeline stage class by type name."""

    def decorator(cls: type[PipelineStage]) -> type[PipelineStage]:
        _STAGE_REGISTRY[name] = cls
        return cls

    return decorator


def get_registered_stages() -> dict[str, type[PipelineStage]]:
    """Return a copy of the stage registry."""
    return dict(_STAGE_REGISTRY)


def build_stage(spec: dict[str, Any]) -> PipelineStage:
    """Instantiate a single stage from a config spec."""
    stage_type = spec["type"]
    if stage_type not in _STAGE_REGISTRY:
        available = ", ".join(sorted(_STAGE_REGISTRY)) or "(none)"
        raise KeyError(f"Unknown pipeline stage type '{stage_type}'. Available: {available}")
    cls = _STAGE_REGISTRY[stage_type]
    config = spec.get("config", {})
    stage = cls(**config)
    if "order" in spec:
        stage.order = spec["order"]
    return stage


def build_pipeline_from_config(stages_config: list[dict[str, Any]]) -> PipelineRunner:
    """Build a ``PipelineRunner`` from a declarative stages list."""
    _ensure_builtins_registered()
    stages = [build_stage(spec) for spec in stages_config]
    return PipelineRunner(stages)


def _ensure_builtins_registered() -> None:
    """Import built-in stages so their ``@register`` decorators run."""
    if _STAGE_REGISTRY:
        return
    try:
        import engine.pipeline.stages.cost_guard  # noqa: F401
        import engine.pipeline.stages.input_validation  # noqa: F401
        import engine.pipeline.stages.rate_limit  # noqa: F401
    except ImportError:
        logger.debug("Built-in pipeline stages unavailable", exc_info=True)
