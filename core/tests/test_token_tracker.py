"""Tests for token tracker."""

from engine.llm.token_tracker import TokenTracker


def test_log_and_total():
    t = TokenTracker()
    t.log("n1", 10, 5)
    t.log("n2", 20, 10)
    assert t.total() == {"input": 30, "output": 15}
