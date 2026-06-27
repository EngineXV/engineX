"""Runtime skill loading for event-loop agents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.skills.context import get_skill_filter
from engine.skills.discovery import read_skill_body


def register_skill_tools(tool_registry: Any, *, repo_root: Path | None = None) -> None:
    """Register load_skill for agents with event-loop nodes."""

    def load_skill(name: str) -> dict[str, Any]:
        """Load a skill document by name from ~/.engine/skills or bundled examples."""
        found = read_skill_body(name, repo_root, allowed_names=get_skill_filter())
        if found is None:
            return {"ok": False, "error": f"Skill not found: {name}"}
        entry, body, files = found
        return {
            "ok": True,
            "name": entry.name,
            "description": entry.description,
            "scope": entry.scope,
            "path": entry.path,
            "body": body,
            "files": files,
        }

    tool_registry.register_function(
        load_skill,
        description="Load a skill SKILL.md body by name for guidance during this task.",
    )
