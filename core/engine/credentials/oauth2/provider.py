"""OAuth2 types and configuration"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any


class TokenPlacement(StrEnum):
    """Where to place the access token in HTTP requests"""

    HEADER_BEARER = "header_bearer"
    """Authorization: Bearer <token> (most common)"""

    HEADER_CUSTOM = "header_custom"
    """Custom header name (e.g., X-Access-Token)"""

    QUERY_PARAM = "query_param"
    """Query parameter (e.g., ?access_token=<token>)"""

    BODY_PARAM = "body_param"
    """Form body parameter"""


@dataclass
class OAuth2Token:
    """Represents an OAuth2 token with metadata"""

    access_token: str
    token_type: str = "Bearer"
    expires_at: datetime | None = None
    refresh_token: str | None = None
    scope: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        if self.expires_at is None:
            return False
        buffer = timedelta(minutes=5)
        return datetime.now(UTC) >= (self.expires_at - buffer)

    @property
    def can_refresh(self) -> bool:
        """Check if token can be refreshed (has refresh_token)"""
        return self.refresh_token is not None and self.refresh_token.strip() != ""

    @property
    def expires_in_seconds(self) -> int | None:
        """Get seconds until expiration, or None if no expiration"""
        if self.expires_at is None:
            return None
        delta = self.expires_at - datetime.now(UTC)
        return max(0, int(delta.total_seconds()))

    @classmethod
    def from_token_response(cls, data: dict[str, Any]) -> OAuth2Token:
        """Create OAuth2Token from an OAuth2 token endpoint response"""
        expires_at = None
        if "expires_in" in data:
            expires_at = datetime.now(UTC) + timedelta(seconds=data["expires_in"])

        return cls(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_at=expires_at,
            refresh_token=data.get("refresh_token"),
            scope=data.get("scope"),
            raw_response=data,
        )


@dataclass
class OAuth2Config:
    """Configuration for an OAuth2 provider"""

    # Endpoints (only token_url is strictly required)
    token_url: str
    authorization_url: str | None = None
    revocation_url: str | None = None
    introspection_url: str | None = None

    # Client credentials
    client_id: str = ""
    client_secret: str = ""

    # Scopes
    default_scopes: list[str] = field(default_factory=list)

    # Token placement for API calls (bipartisan model)
    token_placement: TokenPlacement = TokenPlacement.HEADER_BEARER
    custom_header_name: str | None = None
    query_param_name: str = "access_token"

    # Request configuration
    extra_token_params: dict[str, str] = field(default_factory=dict)
    request_timeout: float = 30.0

    # Additional headers for token requests
    extra_headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate configuration"""
        if not self.token_url:
            raise ValueError("token_url is required")

        if self.token_placement == TokenPlacement.HEADER_CUSTOM and not self.custom_header_name:
            raise ValueError("custom_header_name is required when using HEADER_CUSTOM placement")


class OAuth2Error(Exception):
    """OAuth2 protocol error"""

    def __init__(
        self,
        error: str,
        description: str = "",
        status_code: int = 0,
    ):
        self.error = error
        self.description = description
        self.status_code = status_code
        super().__init__(f"{error}: {description}" if description else error)


class TokenExpiredError(OAuth2Error):
    """Raised when a token has expired and cannot be used"""

    def __init__(self, credential_id: str):
        super().__init__(
            error="token_expired",
            description=f"Token for '{credential_id}' has expired",
        )
        self.credential_id = credential_id


class RefreshTokenInvalidError(OAuth2Error):
    """Raised when the refresh token is invalid or revoked"""

    def __init__(self, credential_id: str, reason: str = ""):
        description = f"Refresh token for '{credential_id}' is invalid"
        if reason:
            description += f": {reason}"
        super().__init__(error="invalid_grant", description=description)
        self.credential_id = credential_id
