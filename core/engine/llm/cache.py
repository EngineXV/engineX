"""Simple in‑memory cache for LLM responses."""

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    response: dict[str, Any]
    model: str
    input_tokens: int
    output_tokens: int


class LLMResponseCache:
    """Thread‑safe cache that maps a request fingerprint to a past response."""

    def __init__(self) -> None:
        self._store: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _fingerprint(
        messages: list[dict[str, Any]],
        system: str,
        tools: list[dict[str, Any]] | None,
        model: str,
        **extra: Any,
    ) -> str:
        """Create a deterministic hash from the request parameters."""
        payload: dict[str, Any] = {
            "messages": messages,
            "system": system,
            "tools": tools,
            "model": model,
        }
        payload.update(extra)
        raw = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[dict[str, Any]] | None,
        model: str,
        **extra: Any,
    ) -> CacheEntry | None:
        key = self._fingerprint(messages, system, tools, model, **extra)
        with self._lock:
            return self._store.get(key)

    def set(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[dict[str, Any]] | None,
        model: str,
        response: dict[str, Any],
        input_tokens: int,
        output_tokens: int,
        **extra: Any,
    ) -> None:
        key = self._fingerprint(messages, system, tools, model, **extra)
        entry = CacheEntry(
            response=response,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        with self._lock:
            self._store[key] = entry

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
