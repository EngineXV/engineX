#!/usr/bin/env python3
"""Generate a JSON load‑test report from latency data."""

import json
import sys


def generate_report(times: list[float], concurrency: int) -> str:
    sorted_times = sorted(times)
    n = len(sorted_times)
    p50 = sorted_times[int(n * 0.5)]
    p95 = sorted_times[min(int(n * 0.95), n - 1)]
    return json.dumps(
        {
            "total_runs": n,
            "concurrency": concurrency,
            "average": sum(times) / n,
            "p50": p50,
            "p95": p95,
            "min": sorted_times[0],
            "max": sorted_times[-1],
        },
        indent=2,
    )


if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    print(generate_report(data, int(sys.argv[1]) if len(sys.argv) > 1 else 1))
