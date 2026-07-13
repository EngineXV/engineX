"""Configuration helpers for the vector store."""

import json
from pathlib import Path
from typing import Any

ENGINE_CONFIG_FILE = Path.home() / ".engine" / "configuration.json"


def _load_config() -> dict[str, Any]:
    if not ENGINE_CONFIG_FILE.exists():
        return {}
    try:
        with open(ENGINE_CONFIG_FILE, encoding="utf-8-sig") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def get_vector_store_config() -> dict[str, Any]:
    """Return vector store settings from the Engine config."""
    config = _load_config()
    return config.get("vector_store", {})
