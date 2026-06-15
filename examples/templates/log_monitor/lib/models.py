"""Shared types for log monitor pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Severity = Literal["SEVERE", "HIGH", "MEDIUM", "LOW"]


@dataclass
class LogEntry:
    timestamp: str
    service: str
    level: str
    message: str
    labels: dict[str, str] = field(default_factory=dict)
    trace_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "service": self.service,
            "level": self.level,
            "message": self.message,
            "labels": self.labels,
            "trace_id": self.trace_id,
        }


@dataclass
class Incident:
    fingerprint: str
    service: str
    level: str
    message: str
    count: int
    severity: Severity
    score: int
    ambiguous: bool
    reasoning: str
    owner: str = ""
    deploy_note: str = ""
    metric_note: str = ""
    sample_timestamps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "service": self.service,
            "level": self.level,
            "message": self.message,
            "count": self.count,
            "severity": self.severity,
            "score": self.score,
            "ambiguous": self.ambiguous,
            "reasoning": self.reasoning,
            "owner": self.owner,
            "deploy_note": self.deploy_note,
            "metric_note": self.metric_note,
            "sample_timestamps": self.sample_timestamps,
        }
