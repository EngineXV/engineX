"""Cost alert store — 3× median run cost alert rule.

Implements the alert rule documented in issue #45:

    RULE: single_run_cost_anomaly
      condition: run_cost_usd > 3 × p50(last_50_runs_for_agent)
      severity: warning
      outputs:
        - Append to ~/.engine/agents/{agent_id}/cost_alerts.jsonl
        - Included in RunSummaryLog.needs_attention flags
        - Surfaced by ``engine cost-tree`` CLI command

Usage::

    store = CostAlertStore(agent_id="my-agent")
    store.record_run_cost(session_id="session_...", cost_usd=0.05)
    alert = store.check_alert(session_id="session_...", cost_usd=0.05)
    if alert:
        print(f"⚠ Cost spike: {alert.ratio:.1f}× median")
"""

from __future__ import annotations

import json
import logging
import statistics
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

#: How many historical run costs to keep per agent for median calculation.
ROLLING_WINDOW = 50

#: Threshold multiplier: fire an alert when run_cost > THRESHOLD × median.
ALERT_THRESHOLD = 3.0

#: Minimum number of historical runs required before alerts are evaluated.
#: Avoids false positives during the first few runs.
MIN_RUNS_FOR_ALERT = 5


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class CostAlert(BaseModel):
    """A fired cost anomaly alert for a single run."""

    agent_id: str
    session_id: str
    run_cost_usd: float
    median_cost_usd: float
    ratio: float  # run_cost_usd / median_cost_usd
    threshold: float = ALERT_THRESHOLD
    flags: list[str] = Field(default_factory=list)  # from anomaly detection
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    model_config = {"extra": "allow"}

    @property
    def summary(self) -> str:
        """One-line human-readable summary."""
        return (
            f"Cost spike: ${self.run_cost_usd:.6f} is "
            f"{self.ratio:.1f}× the median (${self.median_cost_usd:.6f}) "
            f"for agent '{self.agent_id}'"
        )


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class CostAlertStore:
    """Persistent cost statistics and alert evaluation per agent.

    Files written under ``~/.engine/agents/{agent_id}/``:

    * ``cost_stats.json`` — rolling window of historical run costs.
    * ``cost_alerts.jsonl`` — append-only log of every fired alert.
    """

    def __init__(self, agent_id: str, base_dir: Path | None = None) -> None:
        self._agent_id = agent_id
        self._base_dir = base_dir or (Path.home() / ".engine" / "agents" / agent_id)
        self._stats_path = self._base_dir / "cost_stats.json"
        self._alerts_path = self._base_dir / "cost_alerts.jsonl"
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_run_cost(self, session_id: str, cost_usd: float) -> None:
        """Append *cost_usd* to the rolling history for this agent.

        Thread-safe; persists to ``cost_stats.json`` immediately.
        """
        with self._lock:
            stats = self._load_stats()
            history: list[dict[str, Any]] = stats.get("history", [])
            history.append(
                {
                    "session_id": session_id,
                    "cost_usd": cost_usd,
                    "recorded_at": datetime.now(UTC).isoformat(),
                }
            )
            # Keep only the last ROLLING_WINDOW entries
            history = history[-ROLLING_WINDOW:]
            stats["history"] = history
            self._save_stats(stats)

    def check_alert(
        self,
        session_id: str,
        cost_usd: float,
        *,
        flags: list[str] | None = None,
    ) -> CostAlert | None:
        """Evaluate the 3× median alert rule for *cost_usd*.

        Returns a ``CostAlert`` if the rule fires; ``None`` otherwise.
        The alert is **also appended to ``cost_alerts.jsonl``** when it fires.

        Parameters
        ----------
        session_id:
            The session whose cost is being evaluated.
        cost_usd:
            Total USD cost for the session.
        flags:
            Optional anomaly flags from ``detect_anomalies()``; included in
            the alert record.
        """
        with self._lock:
            stats = self._load_stats()
            history: list[dict[str, Any]] = stats.get("history", [])

            # Exclude the current run from median calculation (it was already
            # recorded by record_run_cost, so we look at all *other* entries).
            other_costs = [
                r["cost_usd"]
                for r in history
                if r["session_id"] != session_id and isinstance(r.get("cost_usd"), int | float)
            ]

            if len(other_costs) < MIN_RUNS_FOR_ALERT:
                return None  # Not enough history yet

            median_cost = statistics.median(other_costs)
            if median_cost <= 0:
                return None  # Avoid division by zero / trivial baseline

            ratio = cost_usd / median_cost
            if ratio <= ALERT_THRESHOLD:
                return None

            alert = CostAlert(
                agent_id=self._agent_id,
                session_id=session_id,
                run_cost_usd=cost_usd,
                median_cost_usd=median_cost,
                ratio=ratio,
                threshold=ALERT_THRESHOLD,
                flags=flags or [],
            )
            self._append_alert(alert)
            return alert

    def load_alerts(self, *, limit: int = 50) -> list[CostAlert]:
        """Return the most recent *limit* fired alerts for this agent."""
        if not self._alerts_path.exists():
            return []
        alerts: list[CostAlert] = []
        try:
            with open(self._alerts_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        alerts.append(CostAlert(**json.loads(line)))
                    except Exception:
                        continue
        except OSError:
            return []
        return alerts[-limit:]

    def get_median_cost(self) -> float | None:
        """Return the current median run cost, or ``None`` if insufficient history."""
        with self._lock:
            stats = self._load_stats()
            costs = [
                r["cost_usd"]
                for r in stats.get("history", [])
                if isinstance(r.get("cost_usd"), int | float)
            ]
            if len(costs) < MIN_RUNS_FOR_ALERT:
                return None
            return statistics.median(costs)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_stats(self) -> dict[str, Any]:
        """Load cost_stats.json; return empty dict if missing or corrupt."""
        if not self._stats_path.exists():
            return {}
        try:
            return json.loads(self._stats_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_stats(self, stats: dict[str, Any]) -> None:
        """Write cost_stats.json atomically."""
        self._base_dir.mkdir(parents=True, exist_ok=True)
        tmp = self._stats_path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(stats, indent=2), encoding="utf-8")
            tmp.replace(self._stats_path)
        except OSError as exc:
            logger.warning("Failed to save cost stats for %s: %s", self._agent_id, exc)

    def _append_alert(self, alert: CostAlert) -> None:
        """Append one alert to cost_alerts.jsonl."""
        self._base_dir.mkdir(parents=True, exist_ok=True)
        line = json.dumps(alert.model_dump(), ensure_ascii=False) + "\n"
        try:
            with open(self._alerts_path, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError as exc:
            logger.warning("Failed to append cost alert for %s: %s", self._agent_id, exc)
