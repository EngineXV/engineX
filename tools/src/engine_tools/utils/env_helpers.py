"""Environment variable helpers for Engine Tools"""

from __future__ import annotations

import os


def get_env_var(
    name: str,
    default: str | None = None,
    required: bool = False,
) -> str | None:
    """Get an environment variable"""
    value = os.environ.get(name, default)
    if required and value is None:
        raise ValueError(
            f"Required environment variable '{name}' is not set. "
            f"Please set it before using this tool."
        )
    return value
