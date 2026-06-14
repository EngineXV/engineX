"""Observability module for automatic trace correlation and"""

from framework.observability.logging import (
    clear_trace_context,
    configure_logging,
    get_trace_context,
    set_trace_context,
)

__all__ = [
    "configure_logging",
    "get_trace_context",
    "set_trace_context",
    "clear_trace_context",
]
