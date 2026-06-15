"""OAuth2 support for the credential store"""

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
    "OAuth2Error",
    "TokenExpiredError",
    "RefreshTokenInvalidError",
]
