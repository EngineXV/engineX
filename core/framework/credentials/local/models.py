"""Data models for the local credential registry"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from framework.credentials.models import CredentialIdentity


@dataclass
class LocalAccountInfo:
    """A locally-stored named credential account"""

    credential_id: str
    alias: str
    status: str = "unknown"
    identity: CredentialIdentity = field(default_factory=CredentialIdentity)
    last_validated: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def storage_id(self) -> str:
        """The key used in EncryptedFileStorage: '{credential_id}/{alias}'"""
        return f"{self.credential_id}/{self.alias}"

    def to_account_dict(self) -> dict:
        """Format compatible with AccountSelectionScreen and"""
        return {
            "provider": self.credential_id,
            "alias": self.alias,
            "identity": self.identity.to_dict(),
            "integration_id": None,
            "source": "local",
            "status": self.status,
        }
