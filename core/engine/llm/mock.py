"""Mock LLM Provider for testing and structural validation without"""

import json
import re
from collections.abc import AsyncIterator
from typing import Any

from engine.llm.provider import LLMProvider, LLMResponse, Tool
from engine.llm.stream_events import (
    FinishEvent,
    StreamEvent,
    TextDeltaEvent,
    TextEndEvent,
)


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing agents without making real API calls"""

    def __init__(self, model: str = "mock-model"):
        """Initialize the mock LLM provider"""
        self.model = model

    def _extract_output_keys(self, system: str) -> list[str]:
        """Extract expected output keys from the system prompt"""
        keys = []

        # Pattern 1: output_keys: [key1, key2]
        match = re.search(r"output_keys:\s*\[(.*?)\]", system, re.IGNORECASE)
        if match:
            keys_str = match.group(1)
            keys = [k.strip().strip("\"'") for k in keys_str.split(",")]
            return keys

        # Pattern 2: "keys: key1, key2" or "Generate JSON with keys: key1, key2"
        match = re.search(r"(?:keys|with keys):\s*([a-zA-Z0-9_,\s]+)", system, re.IGNORECASE)
        if match:
            keys_str = match.group(1)
            keys = [k.strip() for k in keys_str.split(",") if k.strip()]
            return keys

        # Pattern 3: Look for JSON schema in system prompt
        match = re.search(r'\{[^}]*"([a-zA-Z0-9_]+)":\s*', system)
        if match:
            # Found at least one key in a JSON-like structure
            all_matches = re.findall(r'"([a-zA-Z0-9_]+)":\s*', system)
            if all_matches:
                return list(set(all_matches))

        return keys

    def _generate_mock_response(
        self,
        system: str = "",
        json_mode: bool = False,
    ) -> str:
        """Generate a mock response based on the system prompt and mode"""
        if json_mode:
            # Try to extract expected keys from system prompt
            keys = self._extract_output_keys(system)

            if keys:
                # Generate JSON with the expected keys
                mock_data = {key: f"mock_{key}_value" for key in keys}
                return json.dumps(mock_data, indent=2)
            else:
                # Fallback: generic mock response
                return json.dumps({"result": "mock_result_value"}, indent=2)
        else:
            # Plain text mock response
            return "This is a mock response for testing purposes."

    def complete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
        json_mode: bool = False,
        max_retries: int | None = None,
    ) -> LLMResponse:
        """Generate a mock completion without calling a real LLM"""
        content = self._generate_mock_response(system=system, json_mode=json_mode)

        return LLMResponse(
            content=content,
            model=self.model,
            input_tokens=0,
            output_tokens=0,
            stop_reason="mock_complete",
        )

    async def acomplete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
        json_mode: bool = False,
        max_retries: int | None = None,
    ) -> LLMResponse:
        """Async mock completion (no I/O, returns immediately)"""
        return self.complete(
            messages=messages,
            system=system,
            tools=tools,
            max_tokens=max_tokens,
            response_format=response_format,
            json_mode=json_mode,
            max_retries=max_retries,
        )

    async def stream(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamEvent]:
        """Stream a mock completion as word-level TextDeltaEvents"""
        content = self._generate_mock_response(system=system, json_mode=False)
        words = content.split(" ")
        accumulated = ""

        for i, word in enumerate(words):
            chunk = word if i == 0 else " " + word
            accumulated += chunk
            yield TextDeltaEvent(content=chunk, snapshot=accumulated)

        yield TextEndEvent(full_text=accumulated)
        yield FinishEvent(stop_reason="mock_complete", model=self.model)
