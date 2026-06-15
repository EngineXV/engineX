"""Loop configuration and output accumulation for event-loop nodes"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.graph.conversation import ConversationStore


@dataclass
class LoopConfig:
    """Configuration for the event loop"""

    max_iterations: int = 50
    max_tool_calls_per_turn: int = 30
    judge_every_n_turns: int = 1
    stall_detection_threshold: int = 3
    max_history_tokens: int = 32_000
    store_prefix: str = ""

    tool_call_overflow_margin: float = 0.5

    max_tool_result_chars: int = 30_000
    spillover_dir: str | None = None

    max_stream_retries: int = 3
    stream_retry_backoff_base: float = 2.0
    stream_retry_max_delay: float = 60.0

    tool_doom_loop_threshold: int = 3
    cf_grace_turns: int = 1
    tool_doom_loop_enabled: bool = True


@dataclass
class OutputAccumulator:
    """Accumulates output key-value pairs"""

    values: dict[str, Any] = field(default_factory=dict)
    store: ConversationStore | None = None

    async def set(self, key: str, value: Any) -> None:
        """Set a key-value pair, persisting immediately if store is available"""
        self.values[key] = value
        if self.store:
            cursor = await self.store.read_cursor() or {}
            outputs = cursor.get("outputs", {})
            outputs[key] = value
            cursor["outputs"] = outputs
            await self.store.write_cursor(cursor)

    def get(self, key: str) -> Any | None:
        """Get a value by key, or None if not present"""
        return self.values.get(key)

    def to_dict(self) -> dict[str, Any]:
        """Return a copy of all accumulated values"""
        return dict(self.values)

    def has_all_keys(self, required: list[str]) -> bool:
        """Return True if all required keys are present with non-None values"""
        return all(k in self.values and self.values[k] is not None for k in required)

    @classmethod
    async def restore(cls, store: ConversationStore) -> OutputAccumulator:
        """Restore accumulator state from conversation store cursor"""
        cursor = await store.read_cursor() or {}
        outputs = cursor.get("outputs", {})
        return cls(values=dict(outputs), store=store)
