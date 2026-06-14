"""Main credential store orchestrating storage"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
from typing import Any

from pydantic import SecretStr

from .models import (
    CredentialKey,
    CredentialObject,
    CredentialRefreshError,
    CredentialUsageSpec,
)
from .provider import CredentialProvider, StaticProvider
from .storage import CredentialStorage, EnvVarStorage, InMemoryStorage
from .template import TemplateResolver

logger = logging.getLogger(__name__)


class CredentialStore:
    """Main credential store orchestrating storage"""

    def __init__(
        self,
        storage: CredentialStorage | None = None,
        providers: list[CredentialProvider] | None = None,
        cache_ttl_seconds: int = 300,
        auto_refresh: bool = True,
    ):
        """Initialize the credential store"""
        self._storage = storage or EnvVarStorage()
        self._providers: dict[str, CredentialProvider] = {}
        self._usage_specs: dict[str, CredentialUsageSpec] = {}

        # Cache: credential_id -> (CredentialObject, cached_at)
        self._cache: dict[str, tuple[CredentialObject, datetime]] = {}
        self._cache_ttl = cache_ttl_seconds
        self._lock = threading.RLock()

        self._auto_refresh = auto_refresh

        # Register providers
        for provider in providers or [StaticProvider()]:
            self.register_provider(provider)

        # Template resolver
        self._resolver = TemplateResolver(self)

    # --- Provider Management ---

    def register_provider(self, provider: CredentialProvider) -> None:
        """Register a credential provider"""
        self._providers[provider.provider_id] = provider
        logger.debug(f"Registered credential provider: {provider.provider_id}")

    def get_provider(self, provider_id: str) -> CredentialProvider | None:
        """Get a provider by ID"""
        return self._providers.get(provider_id)

    def get_provider_for_credential(
        self, credential: CredentialObject
    ) -> CredentialProvider | None:
        """Get the appropriate provider for a credential"""
        # First, check if credential specifies a provider
        if credential.provider_id:
            provider = self._providers.get(credential.provider_id)
            if provider:
                return provider

        # Fall back to finding a provider that supports this type
        for provider in self._providers.values():
            if provider.can_handle(credential):
                return provider

        return None

    # --- Usage Spec Management ---

    def register_usage(self, spec: CredentialUsageSpec) -> None:
        """Register how a tool uses credentials"""
        self._usage_specs[spec.credential_id] = spec

    def get_usage_spec(self, credential_id: str) -> CredentialUsageSpec | None:
        """Get the usage spec for a credential"""
        return self._usage_specs.get(credential_id)

    # --- Credential Access ---

    def get_credential(
        self,
        credential_id: str,
        refresh_if_needed: bool = True,
    ) -> CredentialObject | None:
        """Get a credential by ID"""
        with self._lock:
            # Check cache
            cached = self._get_from_cache(credential_id)
            if cached is not None:
                if refresh_if_needed and self._should_refresh(cached):
                    return self._refresh_credential(cached)
                return cached

            # Load from storage
            credential = self._storage.load(credential_id)
            if credential is None:
                return None

            # Refresh if needed
            if refresh_if_needed and self._should_refresh(credential):
                credential = self._refresh_credential(credential)

            # Cache
            self._add_to_cache(credential)

            return credential

    def get_key(self, credential_id: str, key_name: str) -> str | None:
        """Convenience method to get a specific key value"""
        credential = self.get_credential(credential_id)
        if credential is None:
            return None
        return credential.get_key(key_name)

    def get(self, credential_id: str) -> str | None:
        """Legacy compatibility: get the primary key value"""
        credential = self.get_credential(credential_id)
        if credential is None:
            return None
        return credential.get_default_key()

    # --- Template Resolution ---

    def resolve(self, template: str) -> str:
        """Resolve credential templates in a string"""
        return self._resolver.resolve(template)

    def resolve_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Resolve credential templates in headers dictionary"""
        return self._resolver.resolve_headers(headers)

    def resolve_params(self, params: dict[str, str]) -> dict[str, str]:
        """Resolve credential templates in query parameters dictionary"""
        return self._resolver.resolve_params(params)

    def resolve_for_usage(self, credential_id: str) -> dict[str, Any]:
        """Get resolved request kwargs for a registered usage spec"""
        spec = self._usage_specs.get(credential_id)
        if spec is None:
            raise ValueError(f"No usage spec registered for '{credential_id}'")

        result: dict[str, Any] = {}

        if spec.headers:
            result["headers"] = self.resolve_headers(spec.headers)

        if spec.query_params:
            result["params"] = self.resolve_params(spec.query_params)

        if spec.body_fields:
            result["data"] = {key: self.resolve(value) for key, value in spec.body_fields.items()}

        return result

    # --- Credential Management ---

    def save_credential(self, credential: CredentialObject) -> None:
        """Save a credential to storage"""
        with self._lock:
            self._storage.save(credential)
            self._add_to_cache(credential)
            logger.info(f"Saved credential '{credential.id}'")

    def delete_credential(self, credential_id: str) -> bool:
        """Delete a credential from storage"""
        with self._lock:
            self._remove_from_cache(credential_id)
            result = self._storage.delete(credential_id)
            if result:
                logger.info(f"Deleted credential '{credential_id}'")
            return result

    def list_credentials(self) -> list[str]:
        """List all available credential IDs"""
        return self._storage.list_all()

    def list_accounts(self, provider_name: str) -> list[dict[str, Any]]:
        """List all accounts for a provider type with their identities"""
        if hasattr(self._storage, "load_all_for_provider"):
            creds = self._storage.load_all_for_provider(provider_name)
        else:
            cred = self.get_credential(provider_name)
            creds = [cred] if cred else []
        return [
            {
                "credential_id": c.id,
                "provider": provider_name,
                "alias": c.alias,
                "identity": c.identity.to_dict(),
            }
            for c in creds
        ]

    def get_credential_by_alias(self, provider_name: str, alias: str) -> CredentialObject | None:
        """Find a credential by provider name and alias"""
        # LLMs sometimes pass "provider/alias" as the alias (e.g. "google/wrok"
        # instead of just "wrok").  Strip the provider prefix when present.
        if alias.startswith(f"{provider_name}/"):
            alias = alias[len(provider_name) + 1 :]

        if hasattr(self._storage, "load_by_alias"):
            return self._storage.load_by_alias(provider_name, alias)

        # Scan fallback for storage backends without alias index
        if hasattr(self._storage, "load_all_for_provider"):
            for cred in self._storage.load_all_for_provider(provider_name):
                if cred.alias == alias:
                    return cred
        return None

    def get_credential_by_identity(self, provider_name: str, label: str) -> CredentialObject | None:
        """Alias for get_credential_by_alias (backward compat)"""
        return self.get_credential_by_alias(provider_name, label)

    def is_available(self, credential_id: str) -> bool:
        """Check if a credential is available"""
        return self.get_credential(credential_id, refresh_if_needed=False) is not None

    def exists(self, credential_id: str) -> bool:
        """Check if a credential exists in storage without triggering"""
        return self._storage.exists(credential_id)

    # --- Validation ---

    def validate_for_usage(self, credential_id: str) -> list[str]:
        """Validate that a credential meets its usage spec requirements"""
        spec = self._usage_specs.get(credential_id)
        if spec is None:
            return []  # No requirements registered

        credential = self.get_credential(credential_id)
        if credential is None:
            return [f"Credential '{credential_id}' not found"]

        errors = []
        for key_name in spec.required_keys:
            if not credential.has_key(key_name):
                errors.append(f"Missing required key '{key_name}'")

        return errors

    def validate_all(self) -> dict[str, list[str]]:
        """Validate all registered usage specs"""
        errors = {}
        for cred_id in self._usage_specs.keys():
            cred_errors = self.validate_for_usage(cred_id)
            if cred_errors:
                errors[cred_id] = cred_errors
        return errors

    def validate_credential(self, credential_id: str) -> bool:
        """Validate a credential using its provider"""
        credential = self.get_credential(credential_id, refresh_if_needed=False)
        if credential is None:
            return False

        provider = self.get_provider_for_credential(credential)
        if provider is None:
            # No provider, assume valid if has keys
            return bool(credential.keys)

        return provider.validate(credential)

    # --- Lifecycle Management ---

    def _should_refresh(self, credential: CredentialObject) -> bool:
        """Check if credential should be refreshed"""
        if not self._auto_refresh:
            return False

        if not credential.auto_refresh:
            return False

        provider = self.get_provider_for_credential(credential)
        if provider is None:
            return False

        return provider.should_refresh(credential)

    def _refresh_credential(self, credential: CredentialObject) -> CredentialObject:
        """Refresh a credential using its provider"""
        provider = self.get_provider_for_credential(credential)
        if provider is None:
            logger.warning(f"No provider found for credential '{credential.id}'")
            return credential

        try:
            refreshed = provider.refresh(credential)
            refreshed.last_refreshed = datetime.now(UTC)

            # Persist the refreshed credential
            self._storage.save(refreshed)
            self._add_to_cache(refreshed)

            logger.info(f"Refreshed credential '{credential.id}'")
            return refreshed

        except CredentialRefreshError as e:
            logger.error(f"Failed to refresh credential '{credential.id}': {e}")
            return credential

    def refresh_credential(self, credential_id: str) -> CredentialObject | None:
        """Manually refresh a credential"""
        credential = self.get_credential(credential_id, refresh_if_needed=False)
        if credential is None:
            return None

        return self._refresh_credential(credential)

    # --- Caching ---

    def _get_from_cache(self, credential_id: str) -> CredentialObject | None:
        """Get credential from cache if not expired"""
        if credential_id not in self._cache:
            return None

        credential, cached_at = self._cache[credential_id]
        age = (datetime.now(UTC) - cached_at).total_seconds()

        if age > self._cache_ttl:
            del self._cache[credential_id]
            return None

        return credential

    def _add_to_cache(self, credential: CredentialObject) -> None:
        """Add credential to cache"""
        self._cache[credential.id] = (credential, datetime.now(UTC))

    def _remove_from_cache(self, credential_id: str) -> None:
        """Remove credential from cache"""
        self._cache.pop(credential_id, None)

    def clear_cache(self) -> None:
        """Clear the credential cache"""
        with self._lock:
            self._cache.clear()

    # --- Factory Methods ---

    @classmethod
    def for_testing(
        cls,
        credentials: dict[str, dict[str, str]],
    ) -> CredentialStore:
        """Create a credential store for testing with mock credentials"""
        # Convert test data to CredentialObjects
        cred_objects: dict[str, CredentialObject] = {}

        for cred_id, keys in credentials.items():
            cred_objects[cred_id] = CredentialObject(
                id=cred_id,
                keys={k: CredentialKey(name=k, value=SecretStr(v)) for k, v in keys.items()},
            )

        return cls(
            storage=InMemoryStorage(cred_objects),
            auto_refresh=False,
        )

    @classmethod
    def with_encrypted_storage(
        cls,
        base_path: str | None = None,
        providers: list[CredentialProvider] | None = None,
        **kwargs: Any,
    ) -> CredentialStore:
        """Create a credential store with encrypted file storage"""
        from .storage import EncryptedFileStorage

        return cls(
            storage=EncryptedFileStorage(base_path),
            providers=providers,
            **kwargs,
        )

    @classmethod
    def with_env_storage(
        cls,
        env_mapping: dict[str, str] | None = None,
        providers: list[CredentialProvider] | None = None,
        **kwargs: Any,
    ) -> CredentialStore:
        """Create a credential store with environment variable storage"""
        return cls(
            storage=EnvVarStorage(env_mapping),
            providers=providers,
            **kwargs,
        )

    @classmethod
    def with_engine_sync(
        cls,
        base_url: str = "https://api.localhost",
        cache_ttl_seconds: int = 300,
        local_path: str | None = None,
        auto_sync: bool = True,
        **kwargs: Any,
    ) -> CredentialStore:
        """Create a credential store with Engine server sync"""
        import os
        from pathlib import Path

        from .storage import EncryptedFileStorage

        # Determine local storage path
        if local_path is None:
            local_path = str(Path.home() / ".engine" / "credentials")

        local_storage = EncryptedFileStorage(base_path=local_path)

        # Check if Engine is configured
        api_key = os.environ.get("ENGINE_OAUTH_API_KEY")
        if not api_key:
            logger.info("ENGINE_OAUTH_API_KEY not set, using local-only credential storage")
            return cls(storage=local_storage, **kwargs)

        # Try to setup Engine sync
        try:
            from .engine import (
                EngineCachedStorage,
                EngineClientConfig,
                EngineCredentialClient,
                EngineSyncProvider,
            )

            # Create Engine client
            client = EngineCredentialClient(EngineClientConfig(base_url=base_url))

            # Create sync provider
            provider = EngineSyncProvider(client=client)

            # Use cached storage for offline resilience
            cached_storage = EngineCachedStorage(
                local_storage=local_storage,
                engine_sync_provider=provider,
                cache_ttl_seconds=cache_ttl_seconds,
            )

            store = cls(
                storage=cached_storage,
                providers=[provider],
                auto_refresh=True,
                **kwargs,
            )

            # Initial sync
            if auto_sync:
                synced = provider.sync_all(store)
                logger.info(f"Synced {synced} credentials from Engine server")

            return store

        except ImportError:
            logger.warning("Engine components not available, using local storage")
            return cls(storage=local_storage, **kwargs)

        except Exception as e:
            logger.warning(f"Failed to setup Engine sync: {e}. Using local storage.")
            return cls(storage=local_storage, **kwargs)
