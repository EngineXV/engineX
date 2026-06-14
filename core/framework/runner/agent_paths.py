"""Safe agent path validation for CLI and runtime"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

_ALLOWED_AGENT_ROOTS: tuple[Path, ...] | None = None


def _get_allowed_agent_roots() -> tuple[Path, ...]:
    global _ALLOWED_AGENT_ROOTS
    if _ALLOWED_AGENT_ROOTS is None:
        _ALLOWED_AGENT_ROOTS = (
            (_REPO_ROOT / "exports").resolve(),
            (_REPO_ROOT / "examples").resolve(),
            (Path.home() / ".engine" / "agents").resolve(),
        )
    return _ALLOWED_AGENT_ROOTS


def validate_agent_path(agent_path: str | Path) -> Path:
    """Return resolved path if inside exports/"""
    resolved = Path(agent_path).expanduser().resolve()
    for root in _get_allowed_agent_roots():
        if resolved.is_relative_to(root) and resolved != root:
            return resolved
    raise ValueError(
        "agent_path must be inside an allowed directory (exports/, examples/, or ~/.engine/agents/)"
    )
