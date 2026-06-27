"""Skill discovery for Engine — scans SKILL.md folders on disk."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SKILL_FILENAME = "SKILL.md"
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class SkillEntry:
    name: str
    description: str
    scope: str
    path: str
    enabled: bool = True
    provenance: str = "user"

    def to_row(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "scope": self.scope,
            "path": self.path,
            "enabled": self.enabled,
            "provenance": self.provenance,
        }


def _parse_frontmatter(text: str) -> dict[str, str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    block = match.group(1)
    result: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def _read_skill(skill_file: Path, scope: str, provenance: str = "user") -> SkillEntry | None:
    try:
        text = skill_file.read_text(encoding="utf-8")
    except OSError:
        return None
    meta = _parse_frontmatter(text)
    name = meta.get("name") or skill_file.parent.name
    description = meta.get("description") or ""
    return SkillEntry(
        name=name,
        description=description,
        scope=scope,
        path=str(skill_file.parent.resolve()),
        provenance=provenance,
    )


def _scan_dir(root: Path, scope: str, provenance: str = "user") -> list[SkillEntry]:
    if not root.is_dir():
        return []
    entries: list[SkillEntry] = []
    for skill_file in root.rglob(SKILL_FILENAME):
        entry = _read_skill(skill_file, scope=scope, provenance=provenance)
        if entry:
            entries.append(entry)
    return entries


def discover_skills(repo_root: Path | None = None) -> list[SkillEntry]:
    """Discover skills from user dir, repo, and bundled examples."""
    home = Path.home() / ".engine" / "skills"
    entries = _scan_dir(home, scope="user")
    if repo_root:
        entries.extend(_scan_dir(repo_root / "skills", scope="project", provenance="project"))
        entries.extend(
            _scan_dir(
                repo_root / "examples" / "skills",
                scope="examples",
                provenance="preset",
            )
        )
    # De-dupe by name, prefer user scope
    by_name: dict[str, SkillEntry] = {}
    priority = {"user": 0, "project": 1, "examples": 2}
    for entry in sorted(entries, key=lambda e: priority.get(e.scope, 9)):
        by_name[entry.name] = entry
    return sorted(by_name.values(), key=lambda e: e.name.lower())


def build_skills_prompt_section(
    repo_root: Path | None = None,
    *,
    max_skills: int = 16,
    skill_names: list[str] | None = None,
) -> str:
    """Compact skills index for event-loop system prompts."""
    skills = [s for s in discover_skills(repo_root) if s.enabled]
    if skill_names is None:
        from engine.skills.context import get_skill_filter

        skill_names = get_skill_filter()
    if skill_names:
        allowed = {name.strip().lower() for name in skill_names if name.strip()}
        skills = [s for s in skills if s.name.lower() in allowed]
    skills = skills[:max_skills]
    if not skills:
        return ""
    lines = [
        "## Available Skills",
        "When a skill applies, call `load_skill(name)` to read its full guidance before acting.",
        "",
    ]
    for entry in skills:
        desc = entry.description or "No description"
        lines.append(f"- **{entry.name}** ({entry.scope}): {desc}")
    return "\n".join(lines)


def read_skill_body(
    skill_name: str, repo_root: Path | None = None, *, allowed_names: list[str] | None = None
) -> tuple[SkillEntry, str, list[str]] | None:
    if allowed_names:
        allowed = {name.strip().lower() for name in allowed_names if name.strip()}
        if skill_name.lower() not in allowed:
            return None
    for entry in discover_skills(repo_root):
        if entry.name != skill_name:
            continue
        skill_dir = Path(entry.path)
        skill_file = skill_dir / SKILL_FILENAME
        if not skill_file.is_file():
            return None
        body = skill_file.read_text(encoding="utf-8")
        files = [
            str(p.relative_to(skill_dir))
            for p in skill_dir.rglob("*")
            if p.is_file() and p.name != SKILL_FILENAME
        ]
        return entry, body, sorted(files)
    return None
