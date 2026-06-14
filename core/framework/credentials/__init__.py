"""Credential storage for Engine."""

from .key_storage import (
    delete_oauth_host_api_key,
    generate_and_save_credential_key,
    load_oauth_host_api_key,
    load_credential_key,
    save_oauth_host_api_key,
    save_credential_key,
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
    BearerTokenProvider,
    CredentialProvider,
    StaticProvider,
)
from .setup import (
    CredentialSetupSession,
    MissingCredential,
    SetupResult,
    load_agent_nodes,
    run_credential_setup_cli,
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

# Engine sync components (lazy import to avoid httpx dependency when not needed)
# Usage: from core.framework.credentials.oauth import EngineSyncProvider
# Or: from core.framework.credentials import EngineSyncProvider
try:
    from .engine import (
        EngineCachedStorage,
        EngineClientConfig,
        EngineCredentialClient,
        EngineSyncProvider,
    )

    _OAUTH_HOST_AVAILABLE = True
except ImportError:
    _OAUTH_HOST_AVAILABLE = False

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
    "BearerTokenProvider",
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
    "load_oauth_host_api_key",
    "save_oauth_host_api_key",
    "delete_oauth_host_api_key",
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
    "run_credential_setup_cli",
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
OAUTH_HOST_AVAILABLE = _OAUTH_HOST_AVAILABLE
LOCAL_AVAILABLE = _LOCAL_AVAILABLE
