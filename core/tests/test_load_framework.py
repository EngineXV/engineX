"""Smoke test for load‑test framework."""

import os
import subprocess
import sys


def test_help_runs():
    # Path to tools/ directory at repo root (two levels up from this test file)
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    tool_path = os.path.join(repo_root, "tools", "load_test.py")
    result = subprocess.run(
        [sys.executable, tool_path, "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0 or "usage" in result.stdout.lower()
