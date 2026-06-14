"""Credential specs for Engine tools."""

from .base import CredentialError, CredentialSpec
from .health_check import (
    HealthCheckResult,
    check_credential_health,
    validate_integration_wiring,
)
from .llm import LLM_CREDENTIALS
from .shell_config import (
    add_env_var_to_shell_config,
    detect_shell,
    get_shell_config_path,
    get_shell_source_command,
)
from .store_adapter import CredentialStoreAdapter

CREDENTIAL_SPECS = {**LLM_CREDENTIALS}

__all__ = [
    "CredentialSpec",
    "CredentialStoreAdapter",
    "CredentialError",
    "HealthCheckResult",
    "check_credential_health",
    "validate_integration_wiring",
    "detect_shell",
    "get_shell_config_path",
    "get_shell_source_command",
    "add_env_var_to_shell_config",
    "CREDENTIAL_SPECS",
    "LLM_CREDENTIALS",
]
