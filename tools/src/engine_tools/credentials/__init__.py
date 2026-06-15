"""Credential specs for Engine tools."""

from .base import CredentialError, CredentialSpec
from .health_check import HealthCheckResult, check_credential_health
from .llm import LLM_CREDENTIALS
from .shell_config import check_env_var_in_shell_config, detect_shell, get_shell_config_path
from .store_adapter import CredentialStoreAdapter

CREDENTIAL_SPECS = {**LLM_CREDENTIALS}

__all__ = [
    "CredentialSpec",
    "CredentialStoreAdapter",
    "CredentialError",
    "HealthCheckResult",
    "check_credential_health",
    "check_env_var_in_shell_config",
    "detect_shell",
    "get_shell_config_path",
    "CREDENTIAL_SPECS",
    "LLM_CREDENTIALS",
]
