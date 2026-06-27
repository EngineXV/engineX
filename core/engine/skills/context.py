"""Runtime context for per-agent skill filtering."""

from __future__ import annotations

from contextvars import ContextVar

_skill_filter: ContextVar[list[str] | None] = ContextVar("engine_skill_filter", default=None)


def set_skill_filter(names: list[str] | None) -> None:
    """Restrict skill discovery to the given skill names for the current context."""
    _skill_filter.set(names)


def get_skill_filter() -> list[str] | None:
    return _skill_filter.get()
