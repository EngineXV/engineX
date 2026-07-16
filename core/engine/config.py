"""Shared Engine configuration utilities."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_MAX_TOKENS = 8192
ENGINE_CONFIG_FILE = Path.home() / ".engine" / "configuration.json"

_DEFAULT_CONFIG: dict[str, Any] = {
    "llm": {
        "provider": None,
        "model": None,
        "max_tokens": None,
        "api_key_env_var": None,
        "api_base": None,
        "use_claude_code_subscription": False,
        "use_codex_subscription": False,
    },
    "execution": {
        "max_retries_per_node": 3,
        "max_tool_calls_per_turn": 30,
        "tool_doom_loop_threshold": 3,
        "max_iterations": 50,
        "max_history_tokens": 32000,
        "cost_budget": None,
        "context_policy": None,
    },
    "features": {
        "otel_export": None,
        "prompt_snapshot_storage": True,
        "guardrails_enabled": True,
    },
    "hitl": {
        "minimum_confidence": 0.75,
        "maximum_financial_risk": 0.80,
        "critical_flag_prefixes": ["critical", "fatal", "deny"],
    },
    "pipeline": {
        "cost_guard": {"max_cost_per_request": 1.0},
        "stages": None,
    },
    "agents": {},
}


@dataclass
class EngineConfigValidation:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _bool_env(name: str) -> bool | None:
    value = os.environ.get(name)
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


def _int_env(name: str) -> int | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return None
    return int(value)


def _float_env(name: str) -> float | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return None
    return float(value)


def _normalize_agent_name(agent_name: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", agent_name.upper()).strip("_")


def _load_file_config() -> dict[str, Any]:
    if not ENGINE_CONFIG_FILE.exists():
        return {}
    try:
        with open(ENGINE_CONFIG_FILE, encoding="utf-8-sig") as handle:
            loaded = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _env_overrides() -> dict[str, Any]:
    llm = {}
    execution = {}
    features = {}
    pipeline = {"cost_guard": {}}

    if os.environ.get("ENGINE_LLM_PROVIDER") is not None:
        llm["provider"] = os.environ.get("ENGINE_LLM_PROVIDER")
    if os.environ.get("ENGINE_LLM_MODEL") is not None:
        llm["model"] = os.environ.get("ENGINE_LLM_MODEL")
    if os.environ.get("ENGINE_LLM_MAX_TOKENS") is not None:
        llm["max_tokens"] = _int_env("ENGINE_LLM_MAX_TOKENS")
    if os.environ.get("ENGINE_LLM_API_KEY_ENV_VAR") is not None:
        llm["api_key_env_var"] = os.environ.get("ENGINE_LLM_API_KEY_ENV_VAR")
    if os.environ.get("ENGINE_LLM_API_BASE") is not None:
        llm["api_base"] = os.environ.get("ENGINE_LLM_API_BASE")
    if os.environ.get("ENGINE_LLM_USE_CLAUDE_CODE_SUBSCRIPTION") is not None:
        llm["use_claude_code_subscription"] = _bool_env("ENGINE_LLM_USE_CLAUDE_CODE_SUBSCRIPTION")
    if os.environ.get("ENGINE_LLM_USE_CODEX_SUBSCRIPTION") is not None:
        llm["use_codex_subscription"] = _bool_env("ENGINE_LLM_USE_CODEX_SUBSCRIPTION")

    if os.environ.get("ENGINE_EXECUTION_MAX_RETRIES_PER_NODE") is not None:
        execution["max_retries_per_node"] = _int_env("ENGINE_EXECUTION_MAX_RETRIES_PER_NODE")
    if os.environ.get("ENGINE_EXECUTION_MAX_TOOL_CALLS_PER_TURN") is not None:
        execution["max_tool_calls_per_turn"] = _int_env("ENGINE_EXECUTION_MAX_TOOL_CALLS_PER_TURN")
    if os.environ.get("ENGINE_EXECUTION_TOOL_DOOM_LOOP_THRESHOLD") is not None:
        execution["tool_doom_loop_threshold"] = _int_env(
            "ENGINE_EXECUTION_TOOL_DOOM_LOOP_THRESHOLD"
        )
    if os.environ.get("ENGINE_EXECUTION_MAX_ITERATIONS") is not None:
        execution["max_iterations"] = _int_env("ENGINE_EXECUTION_MAX_ITERATIONS")
    if os.environ.get("ENGINE_EXECUTION_MAX_HISTORY_TOKENS") is not None:
        execution["max_history_tokens"] = _int_env("ENGINE_EXECUTION_MAX_HISTORY_TOKENS")
    if os.environ.get("ENGINE_EXECUTION_COST_BUDGET") is not None:
        execution["cost_budget"] = _float_env("ENGINE_EXECUTION_COST_BUDGET")
    if os.environ.get("ENGINE_EXECUTION_CONTEXT_POLICY") is not None:
        execution["context_policy"] = os.environ.get("ENGINE_EXECUTION_CONTEXT_POLICY")

    if os.environ.get("ENGINE_FEATURE_OTEL_EXPORT") is not None:
        features["otel_export"] = _bool_env("ENGINE_FEATURE_OTEL_EXPORT")
    if os.environ.get("ENGINE_FEATURE_PROMPT_SNAPSHOT_STORAGE") is not None:
        features["prompt_snapshot_storage"] = _bool_env("ENGINE_FEATURE_PROMPT_SNAPSHOT_STORAGE")
    if os.environ.get("ENGINE_FEATURE_GUARDRAILS") is not None:
        features["guardrails_enabled"] = _bool_env("ENGINE_FEATURE_GUARDRAILS")

    if os.environ.get("ENGINE_PIPELINE_COST_GUARD_MAX_COST_PER_REQUEST") is not None:
        pipeline["cost_guard"]["max_cost_per_request"] = _float_env(
            "ENGINE_PIPELINE_COST_GUARD_MAX_COST_PER_REQUEST"
        )

    overrides: dict[str, Any] = {}
    if llm:
        overrides["llm"] = llm
    if execution:
        overrides["execution"] = execution
    if features:
        overrides["features"] = features
    if pipeline["cost_guard"]:
        overrides.setdefault("pipeline", {})["cost_guard"] = pipeline["cost_guard"]
    return overrides


def get_engine_config() -> dict[str, Any]:
    return _merge_dicts(_merge_dicts(_DEFAULT_CONFIG, _load_file_config()), _env_overrides())


def get_agent_config(agent_name: str) -> dict[str, Any]:
    config = get_engine_config()
    agents = config.get("agents", {})
    agent_section = agents.get(agent_name, {}) if isinstance(agents, dict) else {}
    env_prefix = f"ENGINE_AGENT_{_normalize_agent_name(agent_name)}_"
    env_overrides: dict[str, Any] = {}
    for key, env_name in (
        ("model", env_prefix + "MODEL"),
        ("max_tokens", env_prefix + "MAX_TOKENS"),
        ("max_iterations", env_prefix + "MAX_ITERATIONS"),
        ("max_tool_calls_per_turn", env_prefix + "MAX_TOOL_CALLS_PER_TURN"),
        ("max_retries_per_node", env_prefix + "MAX_RETRIES_PER_NODE"),
        ("max_history_tokens", env_prefix + "MAX_HISTORY_TOKENS"),
        ("cost_budget", env_prefix + "COST_BUDGET"),
        ("context_policy", env_prefix + "CONTEXT_POLICY"),
    ):
        if os.environ.get(env_name) is not None:
            if key in {
                "max_tokens",
                "max_iterations",
                "max_tool_calls_per_turn",
                "max_retries_per_node",
                "max_history_tokens",
            }:
                env_overrides[key] = _int_env(env_name)
            elif key == "cost_budget":
                env_overrides[key] = _float_env(env_name)
            else:
                env_overrides[key] = os.environ.get(env_name)
    return _merge_dicts(agent_section if isinstance(agent_section, dict) else {}, env_overrides)


def validate_engine_config() -> EngineConfigValidation:
    errors: list[str] = []
    warnings: list[str] = []

    if ENGINE_CONFIG_FILE.exists():
        try:
            with open(ENGINE_CONFIG_FILE, encoding="utf-8-sig") as handle:
                loaded = json.load(handle)
        except json.JSONDecodeError as exc:
            return EngineConfigValidation(
                valid=False,
                errors=[
                    (
                        f"Invalid JSON in {ENGINE_CONFIG_FILE}: "
                        f"{exc.msg} "
                        f"(line {exc.lineno}, column {exc.colno})"
                    )
                ],
            )
        except OSError as exc:
            return EngineConfigValidation(
                valid=False, errors=[f"Could not read {ENGINE_CONFIG_FILE}: {exc}"]
            )
        if not isinstance(loaded, dict):
            return EngineConfigValidation(
                valid=False, errors=["Top-level configuration must be an object"]
            )
        file_config = loaded
    else:
        file_config = {}
        warnings.append(f"Configuration file not found at {ENGINE_CONFIG_FILE}; using defaults.")

    merged = _merge_dicts(_DEFAULT_CONFIG, file_config)

    try:
        _env_overrides()
    except ValueError as exc:
        errors.append(str(exc))

    llm = merged.get("llm", {}) if isinstance(merged.get("llm"), dict) else {}
    execution = merged.get("execution", {}) if isinstance(merged.get("execution"), dict) else {}
    features = merged.get("features", {}) if isinstance(merged.get("features"), dict) else {}
    hitl = merged.get("hitl", {}) if isinstance(merged.get("hitl"), dict) else {}
    pipeline = merged.get("pipeline", {}) if isinstance(merged.get("pipeline"), dict) else {}

    if llm.get("max_tokens") is not None and (
        not isinstance(llm["max_tokens"], int) or llm["max_tokens"] <= 0
    ):
        errors.append("llm.max_tokens must be a positive integer")
    for key in (
        "max_retries_per_node",
        "max_tool_calls_per_turn",
        "tool_doom_loop_threshold",
        "max_iterations",
        "max_history_tokens",
    ):
        if key in execution and (not isinstance(execution[key], int) or execution[key] < 0):
            errors.append(f"execution.{key} must be a non-negative integer")
    if execution.get("cost_budget") is not None and not isinstance(
        execution["cost_budget"], (int, float)
    ):
        errors.append("execution.cost_budget must be a number")
    if execution.get("context_policy") is not None and not isinstance(
        execution["context_policy"], str
    ):
        errors.append("execution.context_policy must be a string")
    for key in ("otel_export", "prompt_snapshot_storage", "guardrails_enabled"):
        if key in features and features[key] is not None and not isinstance(features[key], bool):
            errors.append(f"features.{key} must be a boolean or null")
    for key in ("minimum_confidence", "maximum_financial_risk"):
        if key in hitl and not isinstance(hitl[key], (int, float)):
            errors.append(f"hitl.{key} must be a number")
    if hitl.get("critical_flag_prefixes") is not None and not isinstance(
        hitl["critical_flag_prefixes"], list
    ):
        errors.append("hitl.critical_flag_prefixes must be a list")
    cost_guard = (
        pipeline.get("cost_guard", {}) if isinstance(pipeline.get("cost_guard"), dict) else {}
    )
    if cost_guard.get("max_cost_per_request") is not None and not isinstance(
        cost_guard["max_cost_per_request"], (int, float)
    ):
        errors.append("pipeline.cost_guard.max_cost_per_request must be a number")

    agents = merged.get("agents", {}) if isinstance(merged.get("agents"), dict) else {}
    for agent_name, agent_config in agents.items():
        if not isinstance(agent_config, dict):
            errors.append(f"agents.{agent_name} must be an object")
            continue
        for key in ("model", "context_policy"):
            if (
                key in agent_config
                and agent_config[key] is not None
                and not isinstance(agent_config[key], str)
            ):
                errors.append(f"agents.{agent_name}.{key} must be a string")
        for key in (
            "max_tokens",
            "max_iterations",
            "max_tool_calls_per_turn",
            "max_retries_per_node",
            "max_history_tokens",
        ):
            if (
                key in agent_config
                and agent_config[key] is not None
                and not isinstance(agent_config[key], int)
            ):
                errors.append(f"agents.{agent_name}.{key} must be an integer")
        if (
            "cost_budget" in agent_config
            and agent_config["cost_budget"] is not None
            and not isinstance(agent_config["cost_budget"], (int, float))
        ):
            errors.append(f"agents.{agent_name}.cost_budget must be a number")

    return EngineConfigValidation(valid=not errors, errors=errors, warnings=warnings)


def get_pipeline_stages_config() -> list[dict[str, Any]]:
    pipeline = get_engine_config().get("pipeline", {})
    stages = pipeline.get("stages") if isinstance(pipeline, dict) else None
    if not isinstance(stages, list):
        return [
            {"type": "input_validation", "order": 100, "config": {}},
            {"type": "rate_limit", "order": 200, "config": {"max_requests_per_minute": 120}},
        ]
    return stages


def get_preferred_model(agent_name: str | None = None) -> str:
    config = get_agent_config(agent_name) if agent_name else get_engine_config().get("llm", {})
    if not isinstance(config, dict):
        config = {}
    provider = config.get("provider")
    model = config.get("model")
    if provider and model:
        if provider == "ollama":
            provider = "ollama_chat"
        model_str = f"{provider}/{model}"
    else:
        model_str = "anthropic/claude-sonnet-4-20250514"
    if model_str.startswith("ollama/") and not model_str.startswith("ollama_chat/"):
        model_str = "ollama_chat/" + model_str.split("/", 1)[1]
    return model_str


def get_max_tokens(agent_name: str | None = None) -> int:
    config = get_agent_config(agent_name) if agent_name else get_engine_config().get("llm", {})
    if not isinstance(config, dict):
        return DEFAULT_MAX_TOKENS
    value = config.get("max_tokens")
    return value if isinstance(value, int) and value > 0 else DEFAULT_MAX_TOKENS


def get_max_retries_per_node(agent_name: str | None = None) -> int:
    config = (
        get_agent_config(agent_name) if agent_name else get_engine_config().get("execution", {})
    )
    value = config.get("max_retries_per_node", 3) if isinstance(config, dict) else 3
    return value if isinstance(value, int) and value >= 0 else 3


def get_max_tool_calls_per_turn(agent_name: str | None = None) -> int:
    config = (
        get_agent_config(agent_name) if agent_name else get_engine_config().get("execution", {})
    )
    value = config.get("max_tool_calls_per_turn", 30) if isinstance(config, dict) else 30
    return value if isinstance(value, int) and value >= 1 else 30


def get_tool_doom_loop_threshold(agent_name: str | None = None) -> int:
    config = (
        get_agent_config(agent_name) if agent_name else get_engine_config().get("execution", {})
    )
    value = config.get("tool_doom_loop_threshold", 3) if isinstance(config, dict) else 3
    return value if isinstance(value, int) and value >= 1 else 3


def get_max_iterations(agent_name: str | None = None) -> int:
    config = (
        get_agent_config(agent_name) if agent_name else get_engine_config().get("execution", {})
    )
    value = config.get("max_iterations", 50) if isinstance(config, dict) else 50
    return value if isinstance(value, int) and value >= 1 else 50


def get_max_history_tokens(agent_name: str | None = None) -> int:
    config = (
        get_agent_config(agent_name) if agent_name else get_engine_config().get("execution", {})
    )
    value = config.get("max_history_tokens", 32000) if isinstance(config, dict) else 32000
    return value if isinstance(value, int) and value >= 1 else 32000


def get_cost_budget(agent_name: str | None = None) -> float | None:
    config = (
        get_agent_config(agent_name) if agent_name else get_engine_config().get("execution", {})
    )
    value = config.get("cost_budget") if isinstance(config, dict) else None
    return float(value) if isinstance(value, (int, float)) else None


def get_context_policy(agent_name: str | None = None) -> str | None:
    config = (
        get_agent_config(agent_name) if agent_name else get_engine_config().get("execution", {})
    )
    value = config.get("context_policy") if isinstance(config, dict) else None
    return value if isinstance(value, str) else None


def get_feature_flag(name: str) -> bool:
    features = get_engine_config().get("features", {})
    value = features.get(name) if isinstance(features, dict) else None
    if value is None:
        return True
    return bool(value)


def get_hitl_thresholds() -> dict[str, Any]:
    hitl = get_engine_config().get("hitl", {})
    return hitl if isinstance(hitl, dict) else {}


def get_api_key() -> str | None:
    llm = get_engine_config().get("llm", {})
    if not isinstance(llm, dict):
        return None
    if llm.get("use_claude_code_subscription"):
        try:
            from engine.runner.subscription_auth import get_claude_code_token

            token = get_claude_code_token()
            if token:
                return token
        except ImportError:
            pass
    if llm.get("use_codex_subscription"):
        try:
            from engine.runner.subscription_auth import get_codex_token

            token = get_codex_token()
            if token:
                return token
        except ImportError:
            pass
    api_key_env_var = llm.get("api_key_env_var")
    return os.environ.get(api_key_env_var) if api_key_env_var else None


def get_api_base() -> str | None:
    llm = get_engine_config().get("llm", {})
    if isinstance(llm, dict) and llm.get("use_codex_subscription"):
        return "https://chatgpt.com/backend-api/codex"
    return llm.get("api_base") if isinstance(llm, dict) else None


def get_llm_extra_kwargs() -> dict[str, Any]:
    llm = get_engine_config().get("llm", {})
    if not isinstance(llm, dict):
        return {}
    if llm.get("use_claude_code_subscription"):
        api_key = get_api_key()
        if api_key:
            return {"extra_headers": {"authorization": f"Bearer {api_key}"}}
    if llm.get("use_codex_subscription"):
        api_key = get_api_key()
        if api_key:
            headers: dict[str, str] = {
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "CodexBar",
            }
            try:
                from engine.runner.subscription_auth import get_codex_account_id

                account_id = get_codex_account_id()
                if account_id:
                    headers["ChatGPT-Account-Id"] = account_id
            except ImportError:
                pass
            return {"extra_headers": headers, "store": False, "allowed_openai_params": ["store"]}
    return {}


@dataclass
class RuntimeConfig:
    """Agent runtime configuration loaded from ~/.engine/configuration.json."""

    model: str = field(default_factory=get_preferred_model)
    temperature: float = 0.7
    max_tokens: int = field(default_factory=get_max_tokens)
    max_iterations: int = field(default_factory=get_max_iterations)
    max_tool_calls_per_turn: int = field(default_factory=get_max_tool_calls_per_turn)
    max_retries_per_node: int = field(default_factory=get_max_retries_per_node)
    max_history_tokens: int = field(default_factory=get_max_history_tokens)
    cost_budget: float | None = field(default_factory=get_cost_budget)
    context_policy: str | None = field(default_factory=get_context_policy)
    api_key: str | None = field(default_factory=get_api_key)
    api_base: str | None = field(default_factory=get_api_base)
    extra_kwargs: dict[str, Any] = field(default_factory=get_llm_extra_kwargs)
