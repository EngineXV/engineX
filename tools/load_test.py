#!/usr/bin/env python3
"""Minimal load‑test harness for EngineX agents."""

import argparse
import time
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed


def run_agent(agent: str, input_data: str) -> float:
    start = time.time()
    subprocess.run(
        [sys.executable, "engine", "run", agent, "--input", input_data],
        capture_output=True,
        text=True,
    )
    return time.time() - start


def main() -> None:
    parser = argparse.ArgumentParser(description="Load test an EngineX agent")
    parser.add_argument("agent", help="Path to the agent template")
    parser.add_argument("--input", default="{}", help="JSON input for the agent")
    parser.add_argument("--concurrency", type=int, default=2, help="Number of concurrent runs")
    parser.add_argument("--iterations", type=int, default=5, help="Total number of runs")
    args = parser.parse_args()

    times: list[float] = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(run_agent, args.agent, args.input) for _ in range(args.iterations)
        ]
        for future in as_completed(futures):
            times.append(future.result())

    print(f"Ran {len(times)} iterations with concurrency {args.concurrency}")
    print(f"Average latency: {sum(times) / len(times):.2f}s")
    print(f"Min latency: {min(times):.2f}s")
    print(f"Max latency: {max(times):.2f}s")


if __name__ == "__main__":
    main()
