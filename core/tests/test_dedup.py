"""Tests for prompt dedup."""

from engine.llm.dedup import PromptDedup


def test_dedup():
    d = PromptDedup()
    assert not d.is_duplicate([{"role": "user", "content": "hi"}])
    assert d.is_duplicate([{"role": "user", "content": "hi"}])
    assert not d.is_duplicate([{"role": "user", "content": "bye"}])


def test_clear():
    d = PromptDedup()
    d.is_duplicate([{"role": "user", "content": "x"}])
    d.clear()
    assert not d.is_duplicate([{"role": "user", "content": "x"}])
