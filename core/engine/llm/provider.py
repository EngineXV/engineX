"""LLM Provider abstraction for pluggable LLM backends"""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from functools import partial
from typing import Any


@dataclass
class LLMResponse:
    """Response from an LLM call"""

    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = ""
    raw_response: Any = None
    cost_usd: float = 0.0  # USD cost computed from provider response (issue #45)


@dataclass
class Tool:
    """A tool the LLM can use"""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolUse:
    """A tool call requested by the LLM"""

    id: str
    name: str
    input: dict[str, Any]


@dataclass
class ToolResult:
    """Result of executing a tool"""

    tool_use_id: str
    content: str
    is_error: bool = False


class LLMProvider(ABC):
    """Abstract LLM provider - plug in any LLM backend"""

    @abstractmethod
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
        """Generate a completion from the LLM"""
        pass

    async def acomplete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list["Tool"] | None = None,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
        json_mode: bool = False,
        max_retries: int | None = None,
    ) -> "LLMResponse":
        """Async version of complete(). Non-blocking on the event loop"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            partial(
                self.complete,
                messages=messages,
                system=system,
                tools=tools,
                max_tokens=max_tokens,
                response_format=response_format,
                json_mode=json_mode,
                max_retries=max_retries,
            ),
        )

    async def stream(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator["StreamEvent"]:
        """Stream a completion as an async iterator of StreamEvents"""
        from engine.llm.stream_events import (
            FinishEvent,
            TextDeltaEvent,
            TextEndEvent,
        )

        response = await self.acomplete(
            messages=messages,
            system=system,
            tools=tools,
            max_tokens=max_tokens,
        )
        yield TextDeltaEvent(content=response.content, snapshot=response.content)
        yield TextEndEvent(full_text=response.content)
        yield FinishEvent(
            stop_reason=response.stop_reason,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            model=response.model,
        )


# Deferred import target for type annotation
from engine.llm.stream_events import StreamEvent as StreamEvent  # noqa: E402, F401
