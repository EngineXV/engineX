"""OAuth2 support for the credential store"""

from .base_provider import BaseOAuth2Provider
from .google_calendar_provider import GoogleCalendarOAuth2Provider
from .hubspot_provider import HubSpotOAuth2Provider
from .provider import (
    OAuth2Config,
    OAuth2Error,
    OAuth2Token,
    RefreshTokenInvalidError,
    TokenExpiredError,
    TokenPlacement,
)
from .zoho_provider import ZohoOAuth2Provider

__all__ = [
    "BaseOAuth2Provider",
    "GoogleCalendarOAuth2Provider",
    "HubSpotOAuth2Provider",
    "OAuth2Token",
    "OAuth2Config",
    "TokenPlacement",
    "OAuth2Error",
    "TokenExpiredError",
    "RefreshTokenInvalidError",
    "ZohoOAuth2Provider",
]
