"""Smoke test for load‑test framework."""

import subprocess
import sys


def test_help_runs():
    result = subprocess.run(
        [sys.executable, "tools/load_test.py", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0 or "usage" in result.stdout.lower()
