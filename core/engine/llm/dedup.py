"""Prompt deduplication within a session."""

from typing import Any


class PromptDedup:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    def is_duplicate(self, messages: list[dict[str, Any]], system: str = "") -> bool:
        key = system + "||" + "||".join(str(m) for m in messages)
        if key in self._seen:
            return True
        self._seen.add(key)
        return False

    def clear(self) -> None:
        self._seen.clear()
