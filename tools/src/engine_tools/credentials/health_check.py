"""Credential health checks for bundled Engine tools"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx


@dataclass
class HealthCheckResult:
    valid: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class CredentialHealthChecker(Protocol):
    def check(self, credential_value: str) -> HealthCheckResult: ...


class OAuthBearerHealthChecker:
    TIMEOUT = 10.0

    def __init__(self, endpoint: str, service_name: str = "Service") -> None:
        self.endpoint = endpoint
        self.service_name = service_name

    def check(self, access_token: str) -> HealthCheckResult:
        try:
            with httpx.Client(timeout=self.TIMEOUT) as client:
                response = client.get(
                    self.endpoint,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                )
            if response.status_code == 200:
                return HealthCheckResult(
                    valid=True,
                    message=f"{self.service_name} credentials valid",
                )
            if response.status_code == 401:
                return HealthCheckResult(
                    valid=False,
                    message=f"{self.service_name} token is invalid or expired",
                    details={"status_code": 401},
                )
            if response.status_code == 403:
                return HealthCheckResult(
                    valid=False,
                    message=f"{self.service_name} token lacks required scopes",
                    details={"status_code": 403},
                )
            return HealthCheckResult(
                valid=False,
                message=f"{self.service_name} API returned status {response.status_code}",
                details={"status_code": response.status_code},
            )
        except httpx.TimeoutException:
            return HealthCheckResult(
                valid=False,
                message=f"{self.service_name} API request timed out",
                details={"error": "timeout"},
            )
        except httpx.RequestError as exc:
            return HealthCheckResult(
                valid=False,
                message=f"Failed to connect to {self.service_name}: {exc}",
                details={"error": str(exc)},
            )


class BraveSearchHealthChecker:
    ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
    TIMEOUT = 10.0

    def check(self, api_key: str) -> HealthCheckResult:
        try:
            with httpx.Client(timeout=self.TIMEOUT) as client:
                response = client.get(
                    self.ENDPOINT,
                    headers={"X-Subscription-Token": api_key},
                    params={"q": "test", "count": "1"},
                )
            if response.status_code in {200, 429}:
                return HealthCheckResult(valid=True, message="Brave Search API key valid")
            if response.status_code == 401:
                return HealthCheckResult(
                    valid=False,
                    message="Brave Search API key is invalid",
                    details={"status_code": 401},
                )
            return HealthCheckResult(
                valid=False,
                message=f"Brave Search API returned status {response.status_code}",
                details={"status_code": response.status_code},
            )
        except httpx.TimeoutException:
            return HealthCheckResult(
                valid=False,
                message="Brave Search API request timed out",
                details={"error": "timeout"},
            )
        except httpx.RequestError as exc:
            return HealthCheckResult(
                valid=False,
                message=f"Failed to connect to Brave Search: {exc}",
                details={"error": str(exc)},
            )


class GoogleSearchHealthChecker:
    ENDPOINT = "https://www.googleapis.com/customsearch/v1"
    TIMEOUT = 10.0

    def check(self, api_key: str, cse_id: str | None = None) -> HealthCheckResult:
        if not cse_id:
            return HealthCheckResult(
                valid=True,
                message="Google API key format valid (CSE ID needed for full check)",
                details={"partial_check": True},
            )
        try:
            with httpx.Client(timeout=self.TIMEOUT) as client:
                response = client.get(
                    self.ENDPOINT,
                    params={"key": api_key, "cx": cse_id, "q": "test", "num": "1"},
                )
            if response.status_code == 200:
                return HealthCheckResult(
                    valid=True,
                    message="Google Custom Search credentials valid",
                )
            if response.status_code == 403:
                return HealthCheckResult(
                    valid=False,
                    message="Google API key is invalid or quota exceeded",
                    details={"status_code": 403},
                )
            return HealthCheckResult(
                valid=False,
                message=f"Google API returned status {response.status_code}",
                details={"status_code": response.status_code},
            )
        except httpx.TimeoutException:
            return HealthCheckResult(
                valid=False,
                message="Google API request timed out",
                details={"error": "timeout"},
            )
        except httpx.RequestError as exc:
            return HealthCheckResult(
                valid=False,
                message=f"Failed to connect to Google API: {exc}",
                details={"error": str(exc)},
            )


class AnthropicHealthChecker:
    ENDPOINT = "https://api.anthropic.com/v1/messages"
    TIMEOUT = 10.0

    def check(self, api_key: str) -> HealthCheckResult:
        try:
            with httpx.Client(timeout=self.TIMEOUT) as client:
                response = client.post(
                    self.ENDPOINT,
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={"model": "claude-sonnet-4-20250514", "max_tokens": 1, "messages": []},
                )
            if response.status_code in {200, 400, 429}:
                return HealthCheckResult(valid=True, message="Anthropic API key valid")
            if response.status_code == 401:
                return HealthCheckResult(
                    valid=False,
                    message="Anthropic API key is invalid",
                    details={"status_code": 401},
                )
            return HealthCheckResult(
                valid=False,
                message=f"Anthropic API returned status {response.status_code}",
                details={"status_code": response.status_code},
            )
        except httpx.TimeoutException:
            return HealthCheckResult(
                valid=False,
                message="Anthropic API request timed out",
                details={"error": "timeout"},
            )
        except httpx.RequestError as exc:
            return HealthCheckResult(
                valid=False,
                message=f"Failed to connect to Anthropic API: {exc}",
                details={"error": str(exc)},
            )


class ExaSearchHealthChecker:
    ENDPOINT = "https://api.exa.ai/search"
    TIMEOUT = 10.0

    def check(self, api_key: str) -> HealthCheckResult:
        try:
            with httpx.Client(timeout=self.TIMEOUT) as client:
                response = client.post(
                    self.ENDPOINT,
                    headers={"x-api-key": api_key, "Content-Type": "application/json"},
                    json={"query": "test", "numResults": 1},
                )
            if response.status_code in {200, 429}:
                return HealthCheckResult(valid=True, message="Exa Search API key valid")
            if response.status_code == 401:
                return HealthCheckResult(
                    valid=False,
                    message="Exa Search API key is invalid",
                    details={"status_code": 401},
                )
            return HealthCheckResult(
                valid=False,
                message=f"Exa Search API returned status {response.status_code}",
                details={"status_code": response.status_code},
            )
        except httpx.TimeoutException:
            return HealthCheckResult(
                valid=False,
                message="Exa Search API request timed out",
                details={"error": "timeout"},
            )
        except httpx.RequestError as exc:
            return HealthCheckResult(
                valid=False,
                message=f"Failed to connect to Exa Search: {exc}",
                details={"error": str(exc)},
            )


HEALTH_CHECKERS: dict[str, CredentialHealthChecker] = {
    "brave_search": BraveSearchHealthChecker(),
    "google_search": GoogleSearchHealthChecker(),
    "anthropic": AnthropicHealthChecker(),
    "exa_search": ExaSearchHealthChecker(),
}


def check_credential_health(
    credential_name: str,
    credential_value: str,
    **kwargs: Any,
) -> HealthCheckResult:
    checker = HEALTH_CHECKERS.get(credential_name)
    if checker is None:
        endpoint = kwargs.get("health_check_endpoint")
        if endpoint:
            checker = OAuthBearerHealthChecker(
                endpoint=endpoint,
                service_name=credential_name.replace("_", " ").title(),
            )
        else:
            return HealthCheckResult(
                valid=True,
                message=f"No health checker for '{credential_name}', assuming valid",
                details={"no_checker": True},
            )
    if credential_name == "google_search" and "cse_id" in kwargs:
        return GoogleSearchHealthChecker().check(credential_value, kwargs["cse_id"])
    return checker.check(credential_value)


def validate_integration_wiring(credential_name: str) -> list[str]:
    from . import CREDENTIAL_SPECS

    issues: list[str] = []
    spec = CREDENTIAL_SPECS.get(credential_name)
    if spec is None:
        issues.append(f"No CredentialSpec for '{credential_name}'")
        return issues
    if not spec.env_var:
        issues.append("CredentialSpec.env_var is empty")
    if spec.health_check_endpoint and credential_name not in HEALTH_CHECKERS:
        issues.append(f"No dedicated health checker for '{credential_name}'")
    return issues
