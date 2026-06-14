"""Structured logging with automatic trace context propagation"""

import json
import logging
import os
import re
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Context variable for trace propagation
# ContextVar is thread-safe and async-safe - perfect for concurrent agent execution
trace_context: ContextVar[dict[str, Any] | None] = ContextVar("trace_context", default=None)

# ANSI escape code pattern (matches \033[...m or \x1b[...m)
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m|\033\[[0-9;]*m")


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape codes from text for clean JSON logging"""
    return ANSI_ESCAPE_PATTERN.sub("", text)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        # Get trace context for correlation - AUTOMATIC!
        context = trace_context.get() or {}

        # Strip ANSI codes from message for clean JSON output
        message = strip_ansi_codes(record.getMessage())

        # Build base log entry
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": message,
        }

        # Add trace context (trace_id, execution_id, agent_id, etc.) - AUTOMATIC!
        log_entry.update(context)

        # Add custom fields from extra (optional)
        event = getattr(record, "event", None)
        if event is not None:
            if isinstance(event, str):
                log_entry["event"] = strip_ansi_codes(str(event))
            else:
                log_entry["event"] = event

        latency_ms = getattr(record, "latency_ms", None)
        if latency_ms is not None:
            log_entry["latency_ms"] = latency_ms

        tokens_used = getattr(record, "tokens_used", None)
        if tokens_used is not None:
            log_entry["tokens_used"] = tokens_used

        node_id = getattr(record, "node_id", None)
        if node_id is not None:
            log_entry["node_id"] = node_id

        model = getattr(record, "model", None)
        if model is not None:
            log_entry["model"] = model

        # Add exception info if present (strip ANSI codes from exception text too)
        if record.exc_info:
            exception_text = self.formatException(record.exc_info)
            log_entry["exception"] = strip_ansi_codes(exception_text)

        return json.dumps(log_entry)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter for development"""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as human-readable string"""
        # Get trace context - AUTOMATIC!
        context = trace_context.get() or {}
        trace_id = context.get("trace_id", "")
        execution_id = context.get("execution_id", "")
        agent_id = context.get("agent_id", "")

        # Build context prefix
        prefix_parts = []
        if trace_id:
            prefix_parts.append(f"trace:{trace_id[:8]}")
        if execution_id:
            prefix_parts.append(f"exec:{execution_id[-8:]}")
        if agent_id:
            prefix_parts.append(f"agent:{agent_id}")

        context_prefix = f"[{' | '.join(prefix_parts)}] " if prefix_parts else ""

        # Get color
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET

        # Format log level (5 chars wide for alignment)
        level = f"{record.levelname:<8}"

        # Add event if present
        event = ""
        record_event = getattr(record, "event", None)
        if record_event is not None:
            event = f" [{record_event}]"

        # Format message: [LEVEL] [trace context] message
        return f"{color}[{level}]{reset} {context_prefix}{record.getMessage()}{event}"


def configure_logging(
    level: str = "INFO",
    format: str = "auto",  # "json", "human", or "auto"
) -> None:
    """Configure structured logging for the application"""
    # Auto-detect format
    if format == "auto":
        # Use JSON if LOG_FORMAT=json or ENV=production
        log_format_env = os.getenv("LOG_FORMAT", "").lower()
        env = os.getenv("ENV", "development").lower()

        if log_format_env == "json" or env == "production":
            format = "json"
        else:
            format = "human"

    # Select formatter
    if format == "json":
        formatter = StructuredFormatter()
        # Disable colors in third-party libraries when using JSON format
        _disable_third_party_colors()
    else:
        formatter = HumanReadableFormatter()

    # Configure handler
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level.upper())

    # When in JSON mode, configure known third-party loggers to use JSON formatter
    # This ensures libraries like LiteLLM, httpcore also output clean JSON
    if format == "json":
        third_party_loggers = [
            "LiteLLM",
            "httpcore",
            "httpx",
            "openai",
        ]
        for logger_name in third_party_loggers:
            logger = logging.getLogger(logger_name)
            # Clear existing handlers so records propagate to root and use our formatter there
            logger.handlers.clear()
            logger.propagate = True  # Still propagate to root for consistency


def _disable_third_party_colors() -> None:
    """Disable color output in third-party libraries for clean JSON logging"""
    # Set NO_COLOR environment variable (common convention for disabling colors)
    os.environ["NO_COLOR"] = "1"
    os.environ["FORCE_COLOR"] = "0"

    # Disable LiteLLM debug/verbose output colors if available
    try:
        import litellm

        # LiteLLM respects NO_COLOR, but we can also suppress debug info
        if hasattr(litellm, "suppress_debug_info"):
            litellm.suppress_debug_info = True  # type: ignore[attr-defined]
    except (ImportError, AttributeError):
        pass


def set_trace_context(**kwargs: Any) -> None:
    """Set trace context for current execution"""
    current = trace_context.get() or {}
    trace_context.set({**current, **kwargs})


def get_trace_context() -> dict:
    """Get current trace context"""
    context = trace_context.get() or {}
    return context.copy()


def clear_trace_context() -> None:
    """Clear trace context"""
    trace_context.set(None)
