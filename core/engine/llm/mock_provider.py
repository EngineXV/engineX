"""Mock LLM provider that returns canned responses instantly."""

from engine.llm.provider import LLMProvider, LLMResponse, Tool


class MockLLMProvider(LLMProvider):
    """Returns a fixed response without any API call."""

    def __init__(self, canned_response: str = "mock output", model: str = "mock"):
        self.canned_response = canned_response
        self.model = model

    def complete(
        self,
        messages: list[dict],
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 1024,
        response_format: dict | None = None,
        json_mode: bool = False,
        max_retries: int | None = None,
    ) -> LLMResponse:
        return LLMResponse(
            content=self.canned_response,
            model=self.model,
            input_tokens=0,
            output_tokens=0,
        )
