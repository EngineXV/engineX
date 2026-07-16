"""Tests for Engine configuration loading and validation."""

from __future__ import annotations

import json

from engine import config as engine_config


def test_validate_engine_config_accepts_execution_overrides(tmp_path, monkeypatch):
    config_path = tmp_path / "configuration.json"
    config_path.write_text(
        json.dumps(
            {
                "llm": {"provider": "ollama", "model": "qwen2.5:7b"},
                "execution": {"max_retries_per_node": 4, "max_tool_calls_per_turn": 22},
                "agents": {"demo": {"model": "gpt-4o-mini", "max_iterations": 12}},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(engine_config, "ENGINE_CONFIG_FILE", config_path)

    validation = engine_config.validate_engine_config()
    assert validation.valid
    assert engine_config.get_max_retries_per_node() == 4
    assert engine_config.get_max_tool_calls_per_turn() == 22
    assert engine_config.get_agent_config("demo")["model"] == "gpt-4o-mini"


def test_validate_engine_config_rejects_bad_values(tmp_path, monkeypatch):
    config_path = tmp_path / "configuration.json"
    config_path.write_text(
        json.dumps({"execution": {"max_tool_calls_per_turn": "many"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(engine_config, "ENGINE_CONFIG_FILE", config_path)

    validation = engine_config.validate_engine_config()
    assert not validation.valid
    assert any("max_tool_calls_per_turn" in error for error in validation.errors)