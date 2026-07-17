"""Tests for the LLM response cache."""

from engine.llm.cache import LLMResponseCache


class TestLLMResponseCache:
    def test_cache_hit(self):
        cache = LLMResponseCache()
        messages = [{"role": "user", "content": "hello"}]
        cache.set(messages, "", None, "test-model", {"answer": "hi"}, 10, 5)
        entry = cache.get(messages, "", None, "test-model")
        assert entry is not None
        assert entry.response == {"answer": "hi"}

    def test_cache_miss(self):
        cache = LLMResponseCache()
        messages = [{"role": "user", "content": "hello"}]
        assert cache.get(messages, "", None, "test-model") is None

    def test_different_messages_not_equal(self):
        cache = LLMResponseCache()
        cache.set([{"role": "user", "content": "a"}], "", None, "m", {"r": 1}, 0, 0)
        assert cache.get([{"role": "user", "content": "b"}], "", None, "m") is None

    def test_clear(self):
        cache = LLMResponseCache()
        cache.set([{"role": "user", "content": "x"}], "", None, "m", {"r": 2}, 0, 0)
        cache.clear()
        assert cache.get([{"role": "user", "content": "x"}], "", None, "m") is None
