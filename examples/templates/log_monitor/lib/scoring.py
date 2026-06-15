"""Rule-based severity scoring."""

from __future__ import annotations

import hashlib
import os
import re
from collections import defaultdict

from .enrichment import get_metric_note, get_recent_deploy_note, get_service_owner
from .models import Incident, LogEntry, Severity

CUSTOMER_FACING = frozenset(
    {"payments-api", "payment-gateway", "auth-service", "checkout", "api-gateway"}
)
SEVERE_PATTERNS = re.compile(
    r"(panic|fatal|oom|out of memory|data loss|corrupt|security breach|unauthorized access)",
    re.IGNORECASE,
)
HIGH_PATTERNS = re.compile(
    r"(503|502|504|timeout|connection refused|database unavailable|deadlock)",
    re.IGNORECASE,
)


def _normalize_message(message: str) -> str:
    # Collapse numbers, UUIDs, and opaque ids so similar errors share a fingerprint.
    text = message.lower().strip()
    text = re.sub(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "<uuid>",
        text,
    )
    text = re.sub(r"\bid=\S+", "id=<id>", text)
    text = re.sub(r"\b\d+\b", "<n>", text)
    return text[:500]


def fingerprint_for(service: str, level: str, message: str) -> str:
    normalized = _normalize_message(message)
    raw = f"{service}|{level}|{normalized}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _score_to_severity(score: int) -> Severity:
    if score >= 8:
        return "SEVERE"
    if score >= 5:
        return "HIGH"
    if score >= 3:
        return "MEDIUM"
    return "LOW"


def _is_ambiguous(score: int, count: int, service: str) -> bool:
    if 3 <= score <= 5:
        return True
    if service in CUSTOMER_FACING and score == 4:
        return True
    if count >= 5 and score < 8:
        return True
    return False


def group_and_score(entries: list[LogEntry]) -> list[Incident]:
    """Group logs by fingerprint and apply rule-based severity."""
    groups: dict[str, list[LogEntry]] = defaultdict(list)
    for entry in entries:
        fp = fingerprint_for(entry.service, entry.level, entry.message)
        groups[fp].append(entry)

    incidents: list[Incident] = []
    for fp, group in groups.items():
        sample = group[0]
        count = len(group)
        score = 0
        reasons: list[str] = []

        if SEVERE_PATTERNS.search(sample.message):
            score += 5
            reasons.append("critical pattern in message")
        if HIGH_PATTERNS.search(sample.message):
            score += 3
            reasons.append("high-impact infrastructure pattern")
        if sample.level in {"fatal", "panic", "critical"}:
            score += 4
            reasons.append(f"level={sample.level}")
        elif sample.level in {"error", "exception"}:
            score += 2
            reasons.append(f"level={sample.level}")

        if count >= 10:
            score += 3
            reasons.append(f"volume={count}")
        elif count >= 3:
            score += 1
            reasons.append(f"volume={count}")

        if sample.service in CUSTOMER_FACING:
            score += 2
            reasons.append("customer-facing service")

        deploy_note = get_recent_deploy_note(sample.service)
        if "within last 2h" in deploy_note:
            score += 1
            reasons.append("recent deploy")

        severity = _score_to_severity(score)
        ambiguous = _is_ambiguous(score, count, sample.service)
        owner = get_service_owner(sample.service)
        metric_note = get_metric_note(sample.service, count)

        incidents.append(
            Incident(
                fingerprint=fp,
                service=sample.service,
                level=sample.level,
                message=sample.message,
                count=count,
                severity=severity,
                score=score,
                ambiguous=ambiguous,
                reasoning="; ".join(reasons) or "baseline error",
                owner=owner,
                deploy_note=deploy_note,
                metric_note=metric_note,
                sample_timestamps=[e.timestamp for e in group[:5]],
            )
        )

    return sorted(incidents, key=lambda item: (-item.score, item.service))


def mute_minutes() -> int:
    raw = os.environ.get("LOG_MONITOR_MUTE_MINUTES", "30")
    try:
        return max(1, int(raw))
    except ValueError:
        return 30
