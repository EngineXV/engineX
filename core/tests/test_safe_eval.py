"""Security and correctness tests for conditional edge safe_eval."""

import pytest

from engine.graph.safe_eval import safe_eval


class TestSafeEvalAllowed:
    def test_arithmetic(self):
        assert safe_eval("1 + 2 * 3", {}) == 7

    def test_context_variable(self):
        assert safe_eval("score >= 0.8", {"score": 0.9}) is True

    def test_dict_get(self):
        ctx = {"output": {"status": "done"}}
        assert safe_eval('output.get("status") == "done"', ctx) is True

    def test_len_and_comparison(self):
        assert safe_eval("len(items) > 0", {"items": [1, 2]}) is True

    def test_boolean_logic(self):
        assert safe_eval("a and not b", {"a": True, "b": False}) is True

    def test_ternary(self):
        assert safe_eval('"yes" if ok else "no"', {"ok": True}) == "yes"


class TestSafeEvalBlocked:
    def test_import_blocked(self):
        with pytest.raises(NameError):
            safe_eval("__import__('os').system('echo pwned')", {})

    def test_dunder_attribute_blocked(self):
        with pytest.raises(ValueError, match="private attribute"):
            safe_eval("x.__class__", {"x": {}})

    def test_lambda_blocked(self):
        with pytest.raises(ValueError, match="not allowed"):
            safe_eval("(lambda: 1)()", {})

    def test_exec_blocked(self):
        with pytest.raises(NameError):
            safe_eval("exec('print(1)')", {})

    def test_unknown_name(self):
        with pytest.raises(NameError):
            safe_eval("secret_value", {})

    def test_unsafe_function_call(self):
        with pytest.raises(NameError):
            safe_eval("open('/etc/passwd')", {})
