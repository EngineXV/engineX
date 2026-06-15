"""Shell configuration utilities for reading persisted environment variables"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Literal

ShellType = Literal["bash", "zsh", "unknown"]


def detect_shell() -> ShellType:
    """Detect the user's default shell"""
    shell = os.environ.get("SHELL", "")

    if "zsh" in shell:
        return "zsh"
    if "bash" in shell:
        return "bash"

    home = Path.home()
    if (home / ".zshrc").exists():
        return "zsh"
    if (home / ".bashrc").exists():
        return "bash"
    return "unknown"


def get_shell_config_path(shell_type: ShellType | None = None) -> Path:
    """Get the path to the shell configuration file"""
    if shell_type is None:
        shell_type = detect_shell()

    home = Path.home()
    if shell_type == "zsh":
        return home / ".zshrc"
    if shell_type == "bash":
        return home / ".bashrc"
    return home / ".bashrc"


def check_env_var_in_shell_config(
    env_var: str,
    shell_type: ShellType | None = None,
) -> tuple[bool, str | None]:
    """Check if an environment variable is already set in shell config"""
    config_path = get_shell_config_path(shell_type)

    if not config_path.exists():
        return False, None

    content = config_path.read_text()
    pattern = rf"^export\s+{re.escape(env_var)}=(.+)$"
    match = re.search(pattern, content, re.MULTILINE)

    if match:
        value = match.group(1).strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        return True, value

    return False, None
