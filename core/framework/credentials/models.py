"""Core data models for the credential store"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, SecretStr


def _utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime"""
    return datetime.now(UTC)


class CredentialType(StrEnum):
    """Types of credentials the store can manage"""

    API_KEY = "api_key"
    """Simple API key (e.g., Brave Search, OpenAI)"""

    OAUTH2 = "oauth2"
    """OAuth2 with refresh token support"""

    BASIC_AUTH = "basic_auth"
    """Username/password pair"""

    BEARER_TOKEN = "bearer_token"
    """JWT or bearer token without refresh"""

    CUSTOM = "custom"
    """User-defined credential type"""


class CredentialKey(BaseModel):
    """A single key within a credential object"""

    name: str
    value: SecretStr
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}

    @property
    def is_expired(self) -> bool:
        """Check if this key has expired"""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) >= self.expires_at

    def get_secret_value(self) -> str:
        """Get the actual secret value (use sparingly)"""
        return self.value.get_secret_value()


class CredentialIdentity(BaseModel):
    """Identity information for a credential (whose account is this?)"""

    email: str | None = None
    username: str | None = None
    workspace: str | None = None
    account_id: str | None = None

    @property
    def label(self) -> str:
        """Best human-readable identifier for display"""
        return self.email or self.username or self.workspace or self.account_id or "unknown"

    @property
    def is_known(self) -> bool:
        """Whether any identity field is populated"""
        return bool(self.email or self.username or self.workspace or self.account_id)

    def to_dict(self) -> dict[str, str]:
        """Return only non-None identity fields"""
        return {k: v for k, v in self.model_dump().items() if v is not None}


class CredentialObject(BaseModel):
    """A credential object containing one or more keys"""

    id: str = Field(description="Unique identifier (e.g., 'brave_search', 'github_oauth')")
    credential_type: CredentialType = CredentialType.API_KEY
    keys: dict[str, CredentialKey] = Field(default_factory=dict)

    # Lifecycle management
    provider_id: str | None = Field(
        default=None,
        description="ID of provider responsible for lifecycle (e.g., 'oauth2', 'static')",
    )
    last_refreshed: datetime | None = None
    auto_refresh: bool = False

    # Usage tracking
    last_used: datetime | None = None
    use_count: int = 0

    # Metadata
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    model_config = {"extra": "allow"}

    def get_key(self, key_name: str) -> str | None:
        """Get a specific key's value"""
        key = self.keys.get(key_name)
        if key is None:
            return None
        return key.get_secret_value()

    def set_key(
        self,
        key_name: str,
        value: str,
        expires_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Set or update a key"""
        self.keys[key_name] = CredentialKey(
            name=key_name,
            value=SecretStr(value),
            expires_at=expires_at,
            metadata=metadata or {},
        )
        self.updated_at = datetime.now(UTC)

    def has_key(self, key_name: str) -> bool:
        """Check if a key exists"""
        return key_name in self.keys

    @property
    def needs_refresh(self) -> bool:
        """Check if any key is expired or near expiration"""
        for key in self.keys.values():
            if key.is_expired:
                return True
        return False

    @property
    def is_valid(self) -> bool:
        """Check if credential has at least one non-expired key"""
        if not self.keys:
            return False
        return not all(key.is_expired for key in self.keys.values())

    def record_usage(self) -> None:
        """Record that this credential was used"""
        self.last_used = datetime.now(UTC)
        self.use_count += 1

    def get_default_key(self) -> str | None:
        """Get the default key value"""
        for key_name in ["value", "api_key", "access_token"]:
            if key_name in self.keys:
                return self.get_key(key_name)

        if self.keys:
            first_key = next(iter(self.keys))
            return self.get_key(first_key)

        return None

    @property
    def identity(self) -> CredentialIdentity:
        """Extract identity from ``_identity_*`` keys in the vault"""
        fields = {}
        for key_name, key_obj in self.keys.items():
            if key_name.startswith("_identity_"):
                field_name = key_name[len("_identity_") :]
                if field_name in CredentialIdentity.model_fields:
                    fields[field_name] = key_obj.value.get_secret_value()
        return CredentialIdentity(**fields)

    @property
    def provider_type(self) -> str | None:
        """Return the integration/provider type (e.g. 'google', 'slack')"""
        key = self.keys.get("_integration_type")
        return key.value.get_secret_value() if key else None

    @property
    def alias(self) -> str | None:
        """Return the user-set alias from the Engine platform"""
        key = self.keys.get("_alias")
        return key.value.get_secret_value() if key else None

    def set_identity(self, **fields: str) -> None:
        """Persist identity fields as ``_identity_*`` keys"""
        for field_name, value in fields.items():
            if value:
                self.set_key(f"_identity_{field_name}", value)


class CredentialUsageSpec(BaseModel):
    """Specification for how a tool uses credentials"""

    credential_id: str = Field(description="ID of credential to use (e.g., 'brave_search')")
    required_keys: list[str] = Field(default_factory=list, description="Keys that must be present")

    # Injection templates (bipartisan model)
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Header templates (e.g., {'Authorization': 'Bearer {{access_token}}'})",
    )
    query_params: dict[str, str] = Field(
        default_factory=dict,
        description="Query param templates (e.g., {'api_key': '{{api_key}}'})",
    )
    body_fields: dict[str, str] = Field(
        default_factory=dict,
        description="Request body field templates",
    )

    # Metadata
    required: bool = True
    description: str = ""
    help_url: str = ""

    model_config = {"extra": "allow"}


class CredentialError(Exception):
    """Base exception for credential-related errors"""

    pass


class CredentialNotFoundError(CredentialError):
    """Raised when a referenced credential doesn't exist"""

    pass


class CredentialKeyNotFoundError(CredentialError):
    """Raised when a referenced key doesn't exist in a credential"""

    pass


class CredentialRefreshError(CredentialError):
    """Raised when credential refresh fails"""

    pass


class CredentialValidationError(CredentialError):
    """Raised when credential validation fails"""

    pass


class CredentialDecryptionError(CredentialError):
    """Raised when credential decryption fails"""

    pass
