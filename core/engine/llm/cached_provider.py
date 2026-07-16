"""Cached LiteLLM provider – wraps LiteLLMProvider with response caching."""

from typing import Any

from engine.llm.cache import LLMResponseCache
from engine.llm.litellm import LiteLLMProvider
from engine.llm.provider import LLMResponse, Tool


class CachedLiteLLMProvider(LiteLLMProvider):
    """LiteLLMProvider with an in‑memory response cache."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._cache = LLMResponseCache()

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
        # Check cache
        cache_entry = self._cache.get(
            messages=messages,
            system=system,
            tools=tools,
            model=self.model,
            max_tokens=max_tokens,
            response_format=response_format,
            json_mode=json_mode,
            max_retries=max_retries,
        )
        if cache_entry:
            return LLMResponse(
                content=cache_entry.response.get("content", ""),
                model=cache_entry.model,
                input_tokens=cache_entry.input_tokens,
                output_tokens=cache_entry.output_tokens,
            )

        # Call parent
        response = super().complete(
            messages=messages,
            system=system,
            tools=tools,
            max_tokens=max_tokens,
            response_format=response_format,
            json_mode=json_mode,
            max_retries=max_retries,
        )

        # Store in cache
        self._cache.set(
            messages=messages,
            system=system,
            tools=tools,
            model=self.model,
            response={"content": response.content},
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            max_tokens=max_tokens,
            response_format=response_format,
            json_mode=json_mode,
            max_retries=max_retries,
        )
        return response

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
        cache_entry = self._cache.get(
            messages=messages,
            system=system,
            tools=tools,
            model=self.model,
            max_tokens=max_tokens,
            response_format=response_format,
            json_mode=json_mode,
            max_retries=max_retries,
        )
        if cache_entry:
            return LLMResponse(
                content=cache_entry.response.get("content", ""),
                model=cache_entry.model,
                input_tokens=cache_entry.input_tokens,
                output_tokens=cache_entry.output_tokens,
            )

        response = await super().acomplete(
            messages=messages,
            system=system,
            tools=tools,
            max_tokens=max_tokens,
            response_format=response_format,
            json_mode=json_mode,
            max_retries=max_retries,
        )

        self._cache.set(
            messages=messages,
            system=system,
            tools=tools,
            model=self.model,
            response={"content": response.content},
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            max_tokens=max_tokens,
            response_format=response_format,
            json_mode=json_mode,
            max_retries=max_retries,
        )
        return response
