"""Template resolution system for credential injection"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .models import CredentialKeyNotFoundError, CredentialNotFoundError

if TYPE_CHECKING:
    from .store import CredentialStore


class TemplateResolver:
    """Resolves credential templates like {{cred.key}} into actual values"""

    # Matches {{credential_id}} or {{credential_id.key_name}}
    TEMPLATE_PATTERN = re.compile(r"\{\{([a-zA-Z0-9_-]+)(?:\.([a-zA-Z0-9_-]+))?\}\}")

    def __init__(self, credential_store: CredentialStore):
        """Initialize the template resolver"""
        self._store = credential_store

    def resolve(self, template: str, fail_on_missing: bool = True) -> str:
        """Resolve all credential references in a template string"""

        def replace_match(match: re.Match) -> str:
            cred_id = match.group(1)
            key_name = match.group(2)  # May be None

            credential = self._store.get_credential(cred_id, refresh_if_needed=True)
            if credential is None:
                if fail_on_missing:
                    raise CredentialNotFoundError(f"Credential '{cred_id}' not found")
                return match.group(0)  # Return original template

            # Get specific key or default
            if key_name:
                value = credential.get_key(key_name)
                if value is None:
                    raise CredentialKeyNotFoundError(
                        f"Key '{key_name}' not found in credential '{cred_id}'"
                    )
            else:
                # Use default key
                value = credential.get_default_key()
                if value is None:
                    raise CredentialKeyNotFoundError(f"Credential '{cred_id}' has no keys")

            # Record usage
            credential.record_usage()

            return value

        return self.TEMPLATE_PATTERN.sub(replace_match, template)

    def resolve_headers(
        self,
        header_templates: dict[str, str],
        fail_on_missing: bool = True,
    ) -> dict[str, str]:
        """Resolve templates in a headers dictionary"""
        return {
            key: self.resolve(value, fail_on_missing) for key, value in header_templates.items()
        }

    def resolve_params(
        self,
        param_templates: dict[str, str],
        fail_on_missing: bool = True,
    ) -> dict[str, str]:
        """Resolve templates in a query parameters dictionary"""
        return {key: self.resolve(value, fail_on_missing) for key, value in param_templates.items()}

    def has_templates(self, text: str) -> bool:
        """Check if text contains any credential templates"""
        return bool(self.TEMPLATE_PATTERN.search(text))

    def extract_references(self, text: str) -> list[tuple[str, str | None]]:
        """Extract all credential references from text"""
        return [(match.group(1), match.group(2)) for match in self.TEMPLATE_PATTERN.finditer(text)]

    def validate_references(self, text: str) -> list[str]:
        """Validate all credential references in text without resolving"""
        errors = []
        references = self.extract_references(text)

        for cred_id, key_name in references:
            credential = self._store.get_credential(cred_id, refresh_if_needed=False)

            if credential is None:
                errors.append(f"Credential '{cred_id}' not found")
                continue

            if key_name:
                if not credential.has_key(key_name):
                    errors.append(f"Key '{key_name}' not found in credential '{cred_id}'")
            elif not credential.keys:
                errors.append(f"Credential '{cred_id}' has no keys")

        return errors

    def get_required_credentials(self, text: str) -> list[str]:
        """Get list of credential IDs required by a template string"""
        references = self.extract_references(text)
        return list(dict.fromkeys(cred_id for cred_id, _ in references))
