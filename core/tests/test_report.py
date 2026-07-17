"""Test load‑test report generator via CLI."""

import json
import subprocess
import sys


def test_generate_report():
    times = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = subprocess.run(
        [sys.executable, "tools/report.py", "2"],
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
