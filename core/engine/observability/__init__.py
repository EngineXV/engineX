"""Observability module for automatic trace correlation and cost attribution."""

from engine.observability.cost_alerts import CostAlert, CostAlertStore
from engine.observability.cost_attribution import (
    CostEntry,
    CostTree,
    NodeCostSummary,
    build_cost_tree,
    detect_anomalies,
    format_cost_waterfall,
    run_cost_usd,
)
from engine.observability.logging import (
    clear_trace_context,
    configure_logging,
    get_trace_context,
    set_trace_context,
)

__all__ = [
    # Trace context
    "configure_logging",
    "get_trace_context",
    "set_trace_context",
    "clear_trace_context",
    # Cost attribution (issue #45)
    "CostEntry",
    "CostTree",
    "NodeCostSummary",
    "build_cost_tree",
    "detect_anomalies",
    "format_cost_waterfall",
    "run_cost_usd",
    # Cost alerts (issue #45)
    "CostAlert",
    "CostAlertStore",
]
