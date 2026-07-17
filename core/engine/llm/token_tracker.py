"""Token usage tracker for LLM calls."""

from typing import Any


class TokenTracker:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def log(self, node_id: str, input_tokens: int, output_tokens: int) -> None:
        self.records.append(
            {
                "node_id": node_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
        )

    def total(self) -> dict[str, int]:
        return {
            "input": sum(r["input_tokens"] for r in self.records),
            "output": sum(r["output_tokens"] for r in self.records),
        }
