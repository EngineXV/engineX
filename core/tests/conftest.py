"""Pytest configuration for core test suite."""

from __future__ import annotations

import sys
from pathlib import Path

_TEMPLATES = Path(__file__).resolve().parents[2] / "examples" / "templates"
if _TEMPLATES.is_dir():
    path_str = str(_TEMPLATES)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
