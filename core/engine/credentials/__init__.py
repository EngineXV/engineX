"""Credential storage for Engine."""

from .key_storage import (
    generate_and_save_credential_key,
    load_credential_key,
    load_engine_sync_api_key,
    save_credential_key,
    save_engine_sync_api_key,
)
from .models import (
    CredentialDecryptionError,
    CredentialError,
    CredentialKey,
    CredentialKeyNotFoundError,
    CredentialNotFoundError,
    CredentialObject,
    CredentialRefreshError,
    CredentialType,
    CredentialUsageSpec,
    CredentialValidationError,
)
from .provider import (
    CredentialProvider,
    StaticProvider,
)
from .setup import (
    CredentialSetupSession,
    MissingCredential,
    SetupResult,
    load_agent_nodes,
)
from .storage import (
    CompositeStorage,
    CredentialStorage,
    EncryptedFileStorage,
    EnvVarStorage,
    InMemoryStorage,
)
from .store import CredentialStore
from .template import TemplateResolver
from .validation import (
    CredentialStatus,
    CredentialValidationResult,
    ensure_credential_key_env,
    validate_agent_credentials,
)

# Engine sync (optional — requires httpx when enabled)
try:
    from .engine import (
        EngineCachedStorage,
        EngineClientConfig,
        EngineCredentialClient,
        EngineSyncProvider,
    )

    _ENGINE_SYNC_AVAILABLE = True
except ImportError:
    _ENGINE_SYNC_AVAILABLE = False

# Local credential registry (named API key accounts with identity metadata)
try:
    from .local import LocalAccountInfo, LocalCredentialRegistry

    _LOCAL_AVAILABLE = True
except ImportError:
    _LOCAL_AVAILABLE = False

__all__ = [
    # Main store
    "CredentialStore",
    # Models
    "CredentialObject",
    "CredentialKey",
    "CredentialType",
    "CredentialUsageSpec",
    # Providers
    "CredentialProvider",
    "StaticProvider",
    # Storage backends
    "CredentialStorage",
    "EncryptedFileStorage",
    "EnvVarStorage",
    "InMemoryStorage",
    "CompositeStorage",
    # Template resolution
    "TemplateResolver",
    # Exceptions
    "CredentialError",
    "CredentialNotFoundError",
    "CredentialKeyNotFoundError",
    "CredentialRefreshError",
    "CredentialValidationError",
    "CredentialDecryptionError",
    # Key storage (bootstrap credentials)
    "load_credential_key",
    "save_credential_key",
    "generate_and_save_credential_key",
    "load_engine_sync_api_key",
    "save_engine_sync_api_key",
    # Validation
    "ensure_credential_key_env",
    "validate_agent_credentials",
    "CredentialStatus",
    "CredentialValidationResult",
    # Interactive setup
    "CredentialSetupSession",
    "MissingCredential",
    "SetupResult",
    "load_agent_nodes",
    # Engine sync (optional - requires httpx)
    "EngineSyncProvider",
    "EngineCredentialClient",
    "EngineClientConfig",
    "EngineCachedStorage",
    # Local credential registry (optional - requires cryptography)
    "LocalCredentialRegistry",
    "LocalAccountInfo",
]

# Track Engine availability for runtime checks
ENGINE_SYNC_AVAILABLE = _ENGINE_SYNC_AVAILABLE
LOCAL_AVAILABLE = _LOCAL_AVAILABLE
