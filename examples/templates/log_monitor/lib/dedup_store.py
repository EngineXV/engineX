"""Persistent fingerprint store for deduplication and mute windows."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


DEFAULT_STORE_PATH = Path.home() / ".engine" / "log_monitor" / "seen_fingerprints.json"


class DedupStore:
    """Track seen log fingerprints and mute windows."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DEFAULT_STORE_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"fingerprints": {}, "outcomes": []}
        try:
            with open(self.path, encoding="utf-8") as handle:
                return json.load(handle)
        except (json.JSONDecodeError, OSError):
            return {"fingerprints": {}, "outcomes": []}

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(self._data, handle, indent=2)

    def is_muted(self, fingerprint: str, mute_minutes: int) -> bool:
        record = self._data.get("fingerprints", {}).get(fingerprint)
        if not record:
            return False
        last_seen = float(record.get("last_seen", 0))
        return (time.time() - last_seen) < (mute_minutes * 60)

    def is_alert_on_cooldown(self, fingerprint: str, cooldown_minutes: int) -> bool:
        record = self._data.get("fingerprints", {}).get(fingerprint)
        if not record:
            return False
        last_alert = float(record.get("last_alert_at", 0))
        if last_alert <= 0:
            return False
        return (time.time() - last_alert) < (cooldown_minutes * 60)

    def mark_alert_sent(self, fingerprint: str, severity: str, channel: str) -> None:
        fps = self._data.setdefault("fingerprints", {})
        record = fps.setdefault(fingerprint, {})
        record["last_alert_at"] = time.time()
        record["last_alert_severity"] = severity
        record["last_alert_channel"] = channel
        record.setdefault("last_seen", time.time())
        self._save()

    def mark_seen(self, fingerprint: str, severity: str, action: str) -> None:
        fps = self._data.setdefault("fingerprints", {})
        fps[fingerprint] = {
            "last_seen": time.time(),
            "last_severity": severity,
            "last_action": action,
        }
        self._save()

    def record_outcome(
        self,
        fingerprint: str,
        severity: str,
        action: str,
        human_override: str = "",
    ) -> None:
        self.mark_seen(fingerprint, severity, action)
        outcomes = self._data.setdefault("outcomes", [])
        outcomes.append(
            {
                "fingerprint": fingerprint,
                "severity": severity,
                "action": action,
                "human_override": human_override,
                "recorded_at": time.time(),
            }
        )
        # Keep last 500 outcomes
        if len(outcomes) > 500:
            self._data["outcomes"] = outcomes[-500:]
        self._save()
