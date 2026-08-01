"""Cross-session run history for the ops console."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def collect_run_history(repo_root: Path, *, limit: int = 50) -> list[dict[str, Any]]:
    """Scan agent storage dirs for recent execution summaries."""
    engine_home = Path.home() / ".engine" / "agents"
    if not engine_home.is_dir():
        return []

    rows: list[dict[str, Any]] = []
    for agent_dir in sorted(engine_home.iterdir()):
        if not agent_dir.is_dir():
            continue
        sessions_dir = agent_dir / "sessions"
        if not sessions_dir.is_dir():
            continue
        for session_dir in sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue
            summary_path = session_dir / "logs" / "summary.json"
            state_path = session_dir / "state.json"
            summary = _read_json(summary_path)
            state = _read_json(state_path)
            checkpoint_index = _read_json(session_dir / "checkpoints" / "index.json")
            metrics = (summary or {}).get("metrics") if isinstance(summary, dict) else None
            state_metrics = (state or {}).get("metrics") if isinstance(state, dict) else None
            progress = (state or {}).get("progress") if isinstance(state, dict) else None

            total_tokens = (
                (summary or {}).get("total_tokens")
                or (metrics or {}).get("total_tokens")
                or (progress or {}).get("total_tokens")
                or 0
            )
            estimated_cost_usd = (
                (summary or {}).get("estimated_cost_usd")
                or (metrics or {}).get("estimated_cost_usd")
                or (state_metrics or {}).get("estimated_cost_usd")
                or 0.0
            )
            total_input_tokens = (
                (summary or {}).get("total_input_tokens")
                or (metrics or {}).get("total_input_tokens")
                or (state_metrics or {}).get("total_input_tokens")
                or 0
            )
            total_output_tokens = (
                (summary or {}).get("total_output_tokens")
                or (metrics or {}).get("total_output_tokens")
                or (state_metrics or {}).get("total_output_tokens")
                or 0
            )
            status = "unknown"
            if summary and summary.get("success") is True:
                status = "completed"
            elif summary and summary.get("success") is False:
                status = "failed"
            elif state and state.get("status"):
                status = str(state.get("status"))
            rows.append(
                {
                    "agent": agent_dir.name,
                    "execution_id": session_dir.name,
                    "status": status,
                    "started_at": (summary or state or {}).get("started_at")
                    or (summary or state or {}).get("created_at"),
                    "ended_at": (summary or {}).get("ended_at"),
                    "total_tokens": total_tokens,
                    "total_input_tokens": total_input_tokens,
                    "total_output_tokens": total_output_tokens,
                    "estimated_cost_usd": estimated_cost_usd,
                    "checkpoint_count": (checkpoint_index or {}).get("total_checkpoints", 0),
                    "latest_checkpoint_id": (checkpoint_index or {}).get("latest_checkpoint_id"),
                    "error": (summary or state or {}).get("error"),
                }
            )

    rows.sort(key=lambda row: row.get("started_at") or "", reverse=True)
    return rows[:limit]


def collect_alerts(repo_root: Path, *, limit: int = 20) -> list[dict[str, Any]]:
    """Build lightweight alert rows from recent failed runs."""
    alerts: list[dict[str, Any]] = []
    for row in collect_run_history(repo_root, limit=limit * 3):
        if row.get("status") != "failed":
            continue
        alerts.append(
            {
                "severity": "high",
                "title": f"{row['agent']} run failed",
                "message": row.get("error") or "Execution failed",
                "execution_id": row.get("execution_id"),
                "agent": row.get("agent"),
                "timestamp": row.get("ended_at") or row.get("started_at"),
            }
        )
        if len(alerts) >= limit:
            break
    if not alerts:
        alerts.append(
            {
                "severity": "info",
                "title": "No recent failures",
                "message": "All scanned executions completed without failure alerts.",
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
    return alerts
