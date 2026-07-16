"""Integration test: LiteLLMProvider with response cache."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_litellm():
    with patch("litellm.completion") as mock:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="mocked response"))]
        mock_response.model = "mock-model"
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
        mock.return_value = mock_response
        yield mock


class TestLiteLLMProviderCache:
    def test_cache_hit_skips_llm_call(self, mock_litellm):
        from engine.llm.litellm import LiteLLMProvider

        provider = LiteLLMProvider(model="test-model")
        messages = [{"role": "user", "content": "hello"}]

        resp1 = provider.complete(messages)
        assert resp1.content == "mocked response"
        assert mock_litellm.call_count == 1

        resp2 = provider.complete(messages)
        assert resp2.content == "mocked response"
        assert mock_litellm.call_count == 1  # cache hit, no new call

    def test_different_messages_triggers_new_call(self, mock_litellm):
        from engine.llm.litellm import LiteLLMProvider

        provider = LiteLLMProvider(model="test-model")
        provider.complete([{"role": "user", "content": "a"}])
        assert mock_litellm.call_count == 1
        provider.complete([{"role": "user", "content": "b"}])
        assert mock_litellm.call_count == 2
