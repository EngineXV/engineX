"""Session state schema migration helpers."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 2


def _parse_schema_version(raw: Any) -> int | None:
    """Parse schema version; return None when the on-disk format is already current."""
    if raw is None:
        return 1
    if isinstance(raw, str):
        # Existing Engine sessions use semantic strings such as "1.1".
        if "." in raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def migrate_session_state(state: dict[str, Any]) -> dict[str, Any]:
    """Upgrade session state dict to the current schema version."""
    version = _parse_schema_version(state.get("schema_version", 1))
    if version is None or version >= CURRENT_SCHEMA_VERSION:
        return state

    migrated = dict(state)
    if version == 1:
        # v1 used flat memory keys; v2 nests progress metadata explicitly.
        progress = migrated.setdefault("progress", {})
        if "current_node" not in progress and migrated.get("paused_at"):
            progress["current_node"] = migrated["paused_at"]
        if "node_visit_counts" not in progress and "node_visit_counts" in migrated:
            progress["node_visit_counts"] = migrated.pop("node_visit_counts")
        if "execution_path" not in progress and "execution_path" in migrated:
            progress["path"] = migrated.pop("execution_path")
        migrated["schema_version"] = CURRENT_SCHEMA_VERSION
        version = CURRENT_SCHEMA_VERSION

    return migrated


def migrate_session_file(state_path: Path) -> bool:
    """Migrate one state.json file in place. Returns True when rewritten."""
    if not state_path.exists():
        return False
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Skipping unreadable session state: %s", state_path)
        return False

    migrated = migrate_session_state(state)
    if migrated == state:
        return False

    from engine.utils.io import atomic_write

    with atomic_write(state_path, encoding="utf-8") as f:
        f.write(json.dumps(migrated, indent=2))
    logger.info("Migrated session state schema: %s", state_path)
    return True
