"""OAuth2 support for the credential store"""

from .base_provider import BaseOAuth2Provider
from .provider import (
    OAuth2Config,
    OAuth2Error,
    OAuth2Token,
    RefreshTokenInvalidError,
    TokenExpiredError,
    TokenPlacement,
)

__all__ = [
    "OAuth2Token",
    "OAuth2Config",
    "TokenPlacement",
    "BaseOAuth2Provider",
    "OAuth2Error",
    "TokenExpiredError",
    "RefreshTokenInvalidError",
]
