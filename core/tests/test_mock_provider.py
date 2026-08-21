"""Tests for MockLLMProvider."""

from engine.llm.mock_provider import MockLLMProvider


def test_returns_canned_response():
    provider = MockLLMProvider("hello")
    resp = provider.complete([])
    assert resp.content == "hello"
    assert resp.model == "mock"
