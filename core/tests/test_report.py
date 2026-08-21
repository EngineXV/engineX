"""Test load‑test report generator via CLI."""

import json
import os
import subprocess
import sys


def test_generate_report():
    times = [1.0, 2.0, 3.0, 4.0, 5.0]
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    tool_path = os.path.join(repo_root, "tools", "report.py")
    result = subprocess.run(
        [sys.executable, tool_path, "2"],
        input=json.dumps(times),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["total_runs"] == 5
    assert data["p50"] == 3.0
    assert data["p95"] == 5.0
    assert data["min"] == 1.0
    assert data["max"] == 5.0
