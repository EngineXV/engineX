"""Discover runnable agents under examples/templates and exports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.runner import AgentRunner


def _is_valid_agent_dir(path: Path) -> bool:
    if not path.is_dir():
        return False
    if path.name.startswith("_"):
        return False
    return (path / "agent.json").exists() or (path / "agent.py").exists()


@dataclass
class AgentEntry:
    path: Path
    name: str
    description: str
    node_count: int
    tool_count: int
    category: str
    supervisor: bool = False
    supervisor_name: str = ""
    department: str = ""
    role_title: str = ""

    def to_dict(self, *, is_loaded: bool = False) -> dict:
        row = {
            "path": str(self.path.resolve()),
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "node_count": self.node_count,
            "tool_count": self.tool_count,
            "is_loaded": is_loaded,
        }
        if self.supervisor:
            row["supervisor"] = True
            row["supervisor_name"] = self.supervisor_name
            row["department"] = self.department
            row["role_title"] = self.role_title
        return row


def _entry_from_runner(path: Path, category: str) -> AgentEntry:
    try:
        runner = AgentRunner.load(path, interactive=False, skip_credential_validation=True)
        info = runner.info()
        entry = AgentEntry(
            path=path.resolve(),
            name=info.name,
            description=info.description,
            node_count=info.node_count,
            tool_count=len(info.required_tools),
            category=category,
            supervisor=info.supervisor,
            supervisor_name=info.supervisor_name,
            department=info.department,
            role_title=info.role_title,
        )
        runner.cleanup()
        return entry
    except Exception:
        return AgentEntry(
            path=path.resolve(),
            name=path.name,
            description="",
            node_count=0,
            tool_count=0,
            category=category,
        )


def _scan_category(root: Path, category: str, *, skip: set[str] | None = None) -> list[AgentEntry]:
    if not root.is_dir():
        return []

    skip = skip or set()
    entries: list[AgentEntry] = []
    for child in sorted(root.iterdir()):
        if child.name in skip or not _is_valid_agent_dir(child):
            continue
        entries.append(_entry_from_runner(child, category))
    return entries


def discover_agents(repo_root: Path, loaded_paths: set[str] | None = None) -> dict[str, list[dict]]:
    """Return agents grouped by category for the dashboard."""
    loaded_paths = loaded_paths or set()
    groups = {
        "templates": _scan_category(
            repo_root / "examples" / "templates",
            "templates",
            skip={"supervisors"},
        ),
        "supervisors": _scan_category(
            repo_root / "examples" / "templates" / "supervisors",
            "supervisors",
        ),
        "exports": _scan_category(repo_root / "exports", "exports"),
    }
    return {
        category: [
            entry.to_dict(is_loaded=entry.path.as_posix() in loaded_paths) for entry in entries
        ]
        for category, entries in groups.items()
    }


def resolve_agent_path(repo_root: Path, agent_path: str) -> Path | None:
    """Resolve an agent path string to an absolute directory."""
    raw = Path(agent_path)
    if raw.is_dir() and _is_valid_agent_dir(raw):
        return raw.resolve()

    for candidate in (
        repo_root / agent_path,
        repo_root / "examples" / "templates" / agent_path,
        repo_root / "examples" / "templates" / "supervisors" / agent_path,
        repo_root / "exports" / agent_path,
    ):
        if candidate.is_dir() and _is_valid_agent_dir(candidate):
            return candidate.resolve()
    return None
