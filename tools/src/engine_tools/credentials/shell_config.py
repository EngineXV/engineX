"""Shell configuration utilities for persisting environment variables"""

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
    elif "bash" in shell:
        return "bash"
    else:
        # Try to detect from config file existence
        home = Path.home()
        if (home / ".zshrc").exists():
            return "zsh"
        elif (home / ".bashrc").exists():
            return "bash"
        return "unknown"


def get_shell_config_path(shell_type: ShellType | None = None) -> Path:
    """Get the path to the shell configuration file"""
    if shell_type is None:
        shell_type = detect_shell()

    home = Path.home()

    if shell_type == "zsh":
        return home / ".zshrc"
    elif shell_type == "bash":
        return home / ".bashrc"
    else:
        # Default to .bashrc for unknown shells
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

    # Look for export ENV_VAR=value or export ENV_VAR="value"
    pattern = rf"^export\s+{re.escape(env_var)}=(.+)$"
    match = re.search(pattern, content, re.MULTILINE)

    if match:
        value = match.group(1).strip()
        # Remove surrounding quotes if present
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        return True, value

    return False, None


def add_env_var_to_shell_config(
    env_var: str,
    value: str,
    shell_type: ShellType | None = None,
    comment: str = "Added by Engine credential setup",
) -> tuple[bool, str]:
    """Add an environment variable export to shell config"""
    config_path = get_shell_config_path(shell_type)

    # Quote the value to handle special characters
    export_line = f'export {env_var}="{value}"'

    try:
        if config_path.exists():
            content = config_path.read_text()

            # Check if already exists
            pattern = rf"^export\s+{re.escape(env_var)}=.*$"
            if re.search(pattern, content, re.MULTILINE):
                # Update existing line
                new_content = re.sub(
                    pattern,
                    export_line,
                    content,
                    flags=re.MULTILINE,
                )
                config_path.write_text(new_content)
                return True, str(config_path)

        # Append to file
        with open(config_path, "a") as f:
            f.write(f"\n# {comment}\n")
            f.write(f"{export_line}\n")

        return True, str(config_path)

    except PermissionError:
        return False, f"Permission denied writing to {config_path}"
    except Exception as e:
        return False, str(e)


def remove_env_var_from_shell_config(
    env_var: str,
    shell_type: ShellType | None = None,
) -> tuple[bool, str]:
    """Remove an environment variable from shell config"""
    config_path = get_shell_config_path(shell_type)

    if not config_path.exists():
        return True, "Config file does not exist"

    try:
        content = config_path.read_text()
        lines = content.split("\n")

        new_lines = []
        skip_next_comment = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip comment lines that precede the export
            if stripped.startswith("# Added by Engine"):
                # Check if next non-empty line is the export
                for j in range(i + 1, len(lines)):
                    next_line = lines[j].strip()
                    if next_line:
                        if next_line.startswith(f"export {env_var}="):
                            skip_next_comment = True
                        break
                if skip_next_comment:
                    continue

            # Skip the export line itself
            if stripped.startswith(f"export {env_var}="):
                skip_next_comment = False
                continue

            new_lines.append(line)

        config_path.write_text("\n".join(new_lines))
        return True, str(config_path)

    except PermissionError:
        return False, f"Permission denied writing to {config_path}"
    except Exception as e:
        return False, str(e)


def get_shell_source_command(shell_type: ShellType | None = None) -> str:
    """Get the command to source the shell config file"""
    config_path = get_shell_config_path(shell_type)
    return f"source {config_path}"
