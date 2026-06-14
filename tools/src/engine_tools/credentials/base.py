"""Base classes for credential management"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import dotenv_values

if TYPE_CHECKING:
    pass


@dataclass
class CredentialSpec:
    """Specification for a single credential"""

    env_var: str
    """Environment variable name (e.g., 'BRAVE_SEARCH_API_KEY')"""

    tools: list[str] = field(default_factory=list)
    """Tool names that require this credential (e.g., ['web_search'])"""

    node_types: list[str] = field(default_factory=list)
    """Node types that require this credential (e.g., ['event_loop'])"""

    required: bool = True
    """Whether this credential is required (vs optional)"""

    startup_required: bool = False
    """Whether this credential must be present at server startup (Tier 1)"""

    help_url: str = ""
    """URL where user can obtain this credential"""

    description: str = ""
    """Human-readable description of what this credential is for"""

    # Auth method support
    engine_oauth_supported: bool = False
    """Whether this credential can be obtained via Engine OAuth2 flow"""

    engine_oauth_provider: str = ""
    """Provider name on Engine server (e.g., 'hubspot')"""

    direct_api_key_supported: bool = True
    """Whether users can directly enter an API key"""

    api_key_instructions: str = ""
    """Step-by-step instructions for getting the API key directly"""

    # Health check configuration
    health_check_endpoint: str = ""
    """API endpoint for validating the credential (lightweight check)"""

    health_check_method: str = "GET"
    """HTTP method for health check"""

    # Credential store mapping
    credential_id: str = ""
    """Credential store ID (e.g., 'hubspot' for the CredentialStore)"""

    credential_key: str = "access_token"
    """Key name within the credential (e.g., 'access_token', 'api_key')"""

    credential_group: str = ""
    """Group name for credentials that must be configured together (e.g., 'google_custom_search')"""


class CredentialError(Exception):
    """Raised when required credentials are missing"""

    pass


class CredentialManager:
    """Centralized credential management with agent-aware validation"""

    def __init__(
        self,
        specs: dict[str, CredentialSpec] | None = None,
        _overrides: dict[str, str] | None = None,
        dotenv_path: Path | None = None,
    ):
        """Initialize the credential manager"""
        if specs is None:
            # Lazy import to avoid circular dependency
            from . import CREDENTIAL_SPECS

            specs = CREDENTIAL_SPECS
        self._specs = specs
        self._overrides = _overrides or {}
        self._dotenv_path = dotenv_path
        # Build reverse mapping: tool_name -> credential_name
        self._tool_to_cred: dict[str, str] = {}
        for cred_name, spec in self._specs.items():
            for tool_name in spec.tools:
                self._tool_to_cred[tool_name] = cred_name
        # Build reverse mapping: node_type -> credential_name
        self._node_type_to_cred: dict[str, str] = {}
        for cred_name, spec in self._specs.items():
            for node_type in spec.node_types:
                self._node_type_to_cred[node_type] = cred_name

    @classmethod
    def for_testing(
        cls,
        overrides: dict[str, str],
        specs: dict[str, CredentialSpec] | None = None,
        dotenv_path: Path | None = None,
    ) -> CredentialManager:
        """Create a CredentialManager with test values"""
        return cls(specs=specs, _overrides=overrides, dotenv_path=dotenv_path)

    def _get_raw(self, name: str) -> str | None:
        """Get credential from overrides, os.environ, or .env file"""
        # 1. Check overrides (for testing)
        if name in self._overrides:
            return self._overrides[name]

        spec = self._specs.get(name)
        if spec is None:
            return None

        # 2. Check os.environ (takes precedence)
        env_value = os.environ.get(spec.env_var)
        if env_value:
            return env_value

        # 3. Fallback: read from .env file (hot-reload)
        return self._read_from_dotenv(spec.env_var)

    def _read_from_dotenv(self, env_var: str) -> str | None:
        """Read a single env var from .env file"""
        dotenv_path = self._dotenv_path or Path.cwd() / ".env"
        if not dotenv_path.exists():
            return None

        # dotenv_values reads file without modifying os.environ
        values = dotenv_values(dotenv_path)
        return values.get(env_var)

    def get(self, name: str) -> str | None:
        """Get a credential value by logical name"""
        if name not in self._specs:
            raise KeyError(f"Unknown credential '{name}'. Available: {list(self._specs.keys())}")

        # No caching - read fresh each time for hot-reload support
        return self._get_raw(name)

    def get_spec(self, name: str) -> CredentialSpec:
        """Get the spec for a credential"""
        if name not in self._specs:
            raise KeyError(f"Unknown credential '{name}'")
        return self._specs[name]

    def is_available(self, name: str) -> bool:
        """Check if a credential is available (set and non-empty)"""
        value = self.get(name)
        return value is not None and value != ""

    def get_credential_for_tool(self, tool_name: str) -> str | None:
        """Get the credential name required by a tool"""
        return self._tool_to_cred.get(tool_name)

    def get_missing_for_tools(self, tool_names: list[str]) -> list[tuple[str, CredentialSpec]]:
        """Get list of missing credentials for the given tools"""
        missing: list[tuple[str, CredentialSpec]] = []
        checked: set[str] = set()

        for tool_name in tool_names:
            cred_name = self._tool_to_cred.get(tool_name)
            if cred_name is None:
                # Tool doesn't require credentials
                continue
            if cred_name in checked:
                # Already checked this credential
                continue
            checked.add(cred_name)

            spec = self._specs[cred_name]
            if spec.required and not self.is_available(cred_name):
                missing.append((cred_name, spec))

        return missing

    def validate_for_tools(self, tool_names: list[str]) -> None:
        """Validate that all credentials required by the given tools are"""
        missing = self.get_missing_for_tools(tool_names)

        if missing:
            raise CredentialError(self._format_missing_error(missing, tool_names))

    def _format_missing_error(
        self,
        missing: list[tuple[str, CredentialSpec]],
        tool_names: list[str],
    ) -> str:
        """Format a clear, actionable error message for missing credentials"""
        lines = ["Cannot run agent: Missing credentials\n"]
        lines.append("The following tools require credentials that are not set:\n")

        for _cred_name, spec in missing:
            # Find which of the requested tools need this credential
            affected_tools = [t for t in tool_names if t in spec.tools]
            tools_str = ", ".join(affected_tools)

            lines.append(f"  {tools_str} requires {spec.env_var}")
            if spec.description:
                lines.append(f"    {spec.description}")
            if spec.help_url:
                lines.append(f"    Get an API key at: {spec.help_url}")
            lines.append(f"    Set via: export {spec.env_var}=your_key")
            lines.append("")

        lines.append("Set these environment variables and re-run the agent.")
        return "\n".join(lines)

    def get_missing_for_node_types(self, node_types: list[str]) -> list[tuple[str, CredentialSpec]]:
        """Get list of missing credentials for the given node types"""
        missing: list[tuple[str, CredentialSpec]] = []
        checked: set[str] = set()

        for node_type in node_types:
            cred_name = self._node_type_to_cred.get(node_type)
            if cred_name is None:
                # Node type doesn't require credentials
                continue
            if cred_name in checked:
                # Already checked this credential
                continue
            checked.add(cred_name)

            spec = self._specs[cred_name]
            if spec.required and not self.is_available(cred_name):
                missing.append((cred_name, spec))

        return missing

    def validate_for_node_types(self, node_types: list[str]) -> None:
        """Validate that all credentials required by the given node types are"""
        missing = self.get_missing_for_node_types(node_types)

        if missing:
            raise CredentialError(self._format_missing_node_type_error(missing, node_types))

    def _format_missing_node_type_error(
        self,
        missing: list[tuple[str, CredentialSpec]],
        node_types: list[str],
    ) -> str:
        """Format a clear, actionable error message"""
        lines = ["Cannot run agent: Missing credentials\n"]
        lines.append("The following node types require credentials that are not set:\n")

        for _cred_name, spec in missing:
            # Find which of the requested node types need this credential
            affected_types = [t for t in node_types if t in spec.node_types]
            types_str = ", ".join(affected_types)

            lines.append(f"  {types_str} nodes require {spec.env_var}")
            if spec.description:
                lines.append(f"    {spec.description}")
            if spec.help_url:
                lines.append(f"    Get an API key at: {spec.help_url}")
            lines.append(f"    Set via: export {spec.env_var}=your_key")
            lines.append("")

        lines.append("Set these environment variables and re-run the agent.")
        return "\n".join(lines)

    def validate_startup(self) -> None:
        """Validate that all startup-required credentials are present"""
        missing: list[tuple[str, CredentialSpec]] = []

        for cred_name, spec in self._specs.items():
            if spec.startup_required and not self.is_available(cred_name):
                missing.append((cred_name, spec))

        if missing:
            raise CredentialError(self._format_startup_error(missing))

    def _format_startup_error(
        self,
        missing: list[tuple[str, CredentialSpec]],
    ) -> str:
        """Format a clear, actionable error message"""
        lines = ["Server startup failed: Missing required credentials\n"]

        for _cred_name, spec in missing:
            lines.append(f"  {spec.env_var}")
            if spec.description:
                lines.append(f"    {spec.description}")
            if spec.help_url:
                lines.append(f"    Get an API key at: {spec.help_url}")
            lines.append(f"    Set via: export {spec.env_var}=your_key")
            lines.append("")

        lines.append("Set these environment variables and restart the server.")
        return "\n".join(lines)

    def get_auth_options(self, credential_name: str) -> list[str]:
        """Get available authentication options for a credential"""
        spec = self._specs.get(credential_name)
        if spec is None:
            return ["direct", "custom"]

        options = []
        if spec.engine_oauth_supported:
            options.append("engine")
        if spec.direct_api_key_supported:
            options.append("direct")
        options.append("custom")  # Always available

        return options

    def get_setup_instructions(self, credential_name: str) -> dict:
        """Get setup instructions for a credential"""
        spec = self._specs.get(credential_name)
        if spec is None:
            return {}

        return {
            "env_var": spec.env_var,
            "description": spec.description,
            "help_url": spec.help_url,
            "api_key_instructions": spec.api_key_instructions,
            "engine_oauth_supported": spec.engine_oauth_supported,
            "engine_oauth_provider": spec.engine_oauth_provider,
            "direct_api_key_supported": spec.direct_api_key_supported,
            "credential_id": spec.credential_id,
            "credential_key": spec.credential_key,
        }
