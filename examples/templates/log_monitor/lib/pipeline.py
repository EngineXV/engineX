"""End-to-end monitor tick: fetch → enrich → dedup → score."""

from __future__ import annotations

import json
from typing import Any

from .config import load_config
from .dedup_store import DedupStore
from .grafana_client import query_grafana_logs
from .scoring import group_and_score


def run_monitor_tick(minutes: int | None = None) -> dict[str, Any]:
    """Execute one monitoring cycle and return structured routing context."""
    cfg = load_config()
    lookback = minutes or cfg.lookback_minutes
    entries = query_grafana_logs(minutes=lookback)
    incidents = group_and_score(entries)

    store = DedupStore()
    mute = cfg.mute_minutes

    new_incidents = []
    skipped = 0
    for incident in incidents:
        if store.is_muted(incident.fingerprint, mute):
            skipped += 1
            continue
        new_incidents.append(incident)

    ambiguous = [item for item in new_incidents if item.ambiguous]
    clear = [item for item in new_incidents if not item.ambiguous]

    return {
        "raw_log_count": len(entries),
        "incident_count": len(incidents),
        "new_incident_count": len(new_incidents),
        "skipped_muted_count": skipped,
        "incidents_json": json.dumps([item.to_dict() for item in new_incidents]),
        "clear_incidents_json": json.dumps([item.to_dict() for item in clear]),
        "ambiguous_incidents_json": json.dumps([item.to_dict() for item in ambiguous]),
        "needs_llm_triage": bool(ambiguous),
        "mock_mode": not all(
            [cfg.grafana_url, cfg.grafana_token, cfg.grafana_datasource_uid]
        ),
        "tick_summary": (
            f"Fetched {len(entries)} logs, {len(new_incidents)} new incidents "
            f"({len(ambiguous)} ambiguous, {skipped} muted/skipped)"
        ),
    }
