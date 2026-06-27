"""Google Calendar OAuth2 provider."""

from __future__ import annotations

from ..models import CredentialObject, CredentialType
from .base_provider import BaseOAuth2Provider
from .provider import OAuth2Config

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"

GOOGLE_CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]


class GoogleCalendarOAuth2Provider(BaseOAuth2Provider):
    """Google OAuth2 provider for Calendar API access."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        scopes: list[str] | None = None,
    ) -> None:
        config = OAuth2Config(
            token_url=GOOGLE_TOKEN_URL,
            authorization_url=GOOGLE_AUTHORIZATION_URL,
            client_id=client_id,
            client_secret=client_secret,
            default_scopes=scopes or GOOGLE_CALENDAR_SCOPES,
        )
        super().__init__(config, provider_id="google_calendar_oauth2")

    def get_authorization_url(
        self,
        state: str,
        redirect_uri: str,
        scopes: list[str] | None = None,
        **kwargs,
    ) -> str:
        return super().get_authorization_url(
            state=state,
            redirect_uri=redirect_uri,
            scopes=scopes,
            access_type="offline",
            prompt="consent",
            **kwargs,
        )

    @property
    def supported_types(self) -> list[CredentialType]:
        return [CredentialType.OAUTH2]

    def validate(self, credential: CredentialObject) -> bool:
        access_token = credential.get_key("access_token")
        if not access_token:
            return False
        if super().validate(credential):
            return True
        try:
            client = self._get_client()
            response = client.get(
                "https://www.googleapis.com/calendar/v3/users/me/calendarList",
                params={"maxResults": 1},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return response.status_code == 200
        except Exception:
            return False
