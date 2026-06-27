"""Helpers for HITL review evidence payloads."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from engine.graph.node import NodeSpec, SharedMemory


def _truncate(value: Any, limit: int = 4000) -> str:
    text = value if isinstance(value, str) else str(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def build_hitl_payload(
    *,
    node_id: str,
    node_spec: NodeSpec,
    memory: SharedMemory,
    prompt: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build evidence cards and audit metadata for human review."""
    evidence: list[dict[str, Any]] = []

    for key in node_spec.input_keys or []:
        value = memory.read(key)
        if value is None:
            continue
        evidence.append(
            {
                "id": f"input:{key}",
                "label": key.replace("_", " ").title(),
                "kind": "input",
                "content": _truncate(value),
            }
        )

    for key in node_spec.output_keys or []:
        value = memory.read(key)
        if value is None:
            continue
        evidence.append(
            {
                "id": f"output:{key}",
                "label": key.replace("_", " ").title(),
                "kind": "output",
                "content": _truncate(value),
            }
        )

    attachments: list[dict[str, str]] = []
    for key in (node_spec.input_keys or []) + (node_spec.output_keys or []):
        value = memory.read(key)
        if not isinstance(value, str):
            continue
        lowered = key.lower()
        if any(token in lowered for token in ("path", "file", "document", "attachment")):
            attachments.append({"name": key, "path": value})

    audit_card = {
        "node_id": node_id,
        "node_name": node_spec.name or node_id,
        "reviewed_at": datetime.now(UTC).isoformat(),
        "prompt": prompt,
        "evidence_count": len(evidence),
        "attachment_count": len(attachments),
    }
    if attachments:
        audit_card["attachments"] = attachments

    return evidence, audit_card
