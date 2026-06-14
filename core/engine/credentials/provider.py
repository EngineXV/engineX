"""Provider interface for credential lifecycle management"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta

from .models import CredentialObject, CredentialRefreshError, CredentialType

logger = logging.getLogger(__name__)


class CredentialProvider(ABC):
    """Abstract base class for credential providers"""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for this provider"""
        pass

    @property
    @abstractmethod
    def supported_types(self) -> list[CredentialType]:
        """Credential types this provider can manage"""
        pass

    @abstractmethod
    def refresh(self, credential: CredentialObject) -> CredentialObject:
        """Refresh the credential"""
        pass

    @abstractmethod
    def validate(self, credential: CredentialObject) -> bool:
        """Validate that a credential is still working"""
        pass

    def should_refresh(self, credential: CredentialObject) -> bool:
        """Determine if a credential should be refreshed"""
        buffer = timedelta(minutes=5)
        now = datetime.now(UTC)

        for key in credential.keys.values():
            if key.expires_at is not None:
                if key.expires_at <= now + buffer:
                    return True
        return False

    def revoke(self, credential: CredentialObject) -> bool:
        """Revoke a credential (optional operation)"""
        logger.warning(f"Provider '{self.provider_id}' does not support revocation")
        return False

    def can_handle(self, credential: CredentialObject) -> bool:
        """Check if this provider can handle a credential"""
        return credential.credential_type in self.supported_types


class StaticProvider(CredentialProvider):
    """Provider for static credentials that never need refresh"""

    @property
    def provider_id(self) -> str:
        return "static"

    @property
    def supported_types(self) -> list[CredentialType]:
        return [CredentialType.API_KEY, CredentialType.BASIC_AUTH, CredentialType.CUSTOM]

    def refresh(self, credential: CredentialObject) -> CredentialObject:
        """Static credentials don't need refresh"""
        logger.debug(f"Static credential '{credential.id}' does not need refresh")
        return credential

    def validate(self, credential: CredentialObject) -> bool:
        """Validate that credential has at least one key with a value"""
        if not credential.keys:
            return False

        # Check at least one key has a non-empty value
        for key in credential.keys.values():
            try:
                value = key.get_secret_value()
                if value and value.strip():
                    return True
            except Exception:
                continue

        return False

    def should_refresh(self, credential: CredentialObject) -> bool:
        """Static credentials never need refresh"""
        return False


class BearerTokenProvider(CredentialProvider):
    """Provider for bearer tokens without refresh capability"""

    @property
    def provider_id(self) -> str:
        return "bearer_token"

    @property
    def supported_types(self) -> list[CredentialType]:
        return [CredentialType.BEARER_TOKEN]

    def refresh(self, credential: CredentialObject) -> CredentialObject:
        """Bearer tokens without refresh capability cannot be refreshed"""
        raise CredentialRefreshError(
            f"Bearer token '{credential.id}' cannot be refreshed. "
            "Obtain a new token and save it to the credential store."
        )

    def validate(self, credential: CredentialObject) -> bool:
        """Validate based on expiration time"""
        access_key = credential.keys.get("access_token") or credential.keys.get("token")
        if access_key is None:
            return False

        # Check if expired
        return not access_key.is_expired

    def should_refresh(self, credential: CredentialObject) -> bool:
        """Check if token is expired or near expiration"""
        buffer = timedelta(minutes=5)
        now = datetime.now(UTC)

        for key_name in ["access_token", "token"]:
            key = credential.keys.get(key_name)
            if key and key.expires_at:
                if key.expires_at <= now + buffer:
                    return True

        return False
