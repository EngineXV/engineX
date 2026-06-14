"""Command-line interface for the Engine agent runtime"""

import argparse
import sys
from pathlib import Path


def _configure_paths() -> None:
    """Add exports/ and examples/templates/ to sys.path for agent discovery"""
    engine_dir = Path(__file__).resolve().parent
    project_root = engine_dir.parent.parent

    for subpath in ("exports", "examples/templates"):
        path = project_root / subpath
        if path.is_dir():
            path_str = str(path)
            if path_str not in sys.path:
                sys.path.insert(0, path_str)

    core_str = str(project_root / "core")
    if (project_root / "core").is_dir() and core_str not in sys.path:
        sys.path.insert(0, core_str)


def main() -> None:
    _configure_paths()

    parser = argparse.ArgumentParser(
        prog="engine",
        description="Engine — run goal-driven agents",
    )
    parser.add_argument(
        "--model",
        default="claude-haiku-4-5-20251001",
        help="Anthropic model to use",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    from engine.runner.cli import register_commands

    register_commands(subparsers)

    args = parser.parse_args()
    if hasattr(args, "func"):
        sys.exit(args.func(args))
    parser.print_help()
    sys.exit(1)
