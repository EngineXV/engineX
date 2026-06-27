"""OAuth authorize/callback routes for dashboard credential connect."""

from __future__ import annotations

import logging
import os
import secrets
import time
from typing import Any

from aiohttp import web
from pydantic import SecretStr

from engine.credentials.models import CredentialKey, CredentialObject
from engine.credentials.store import CredentialStore

logger = logging.getLogger(__name__)

_OAUTH_STATE: dict[str, dict[str, Any]] = {}
_STATE_TTL_S = 600.0


def _store(request: web.Request) -> CredentialStore:
    return request.app["credential_store"]


def _redirect_base(request: web.Request) -> str:
    configured = os.environ.get("ENGINE_OAUTH_REDIRECT_URI")
    if configured:
        return configured.rsplit("/", 1)[0] + "/api/oauth/callback"
    host = request.host or "127.0.0.1:8787"
    scheme = request.scheme or "http"
    return f"{scheme}://{host}/api/oauth/callback"


def _provider_for(name: str):
    if name == "hubspot":
        client_id = os.environ.get("HUBSPOT_CLIENT_ID", "")
        client_secret = os.environ.get("HUBSPOT_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            return None
        from engine.credentials.oauth2.hubspot_provider import HubSpotOAuth2Provider

        return HubSpotOAuth2Provider(client_id=client_id, client_secret=client_secret)
    if name == "zoho":
        client_id = os.environ.get("ZOHO_CLIENT_ID", "")
        client_secret = os.environ.get("ZOHO_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            return None
        from engine.credentials.oauth2.zoho_provider import ZohoOAuth2Provider

        return ZohoOAuth2Provider(client_id=client_id, client_secret=client_secret)
    if name in ("google_calendar", "google"):
        client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            return None
        from engine.credentials.oauth2.google_calendar_provider import GoogleCalendarOAuth2Provider

        return GoogleCalendarOAuth2Provider(client_id=client_id, client_secret=client_secret)
    return None


def _cleanup_state() -> None:
    now = time.time()
    stale = [k for k, v in _OAUTH_STATE.items() if now - v.get("created", 0) > _STATE_TTL_S]
    for key in stale:
        _OAUTH_STATE.pop(key, None)


async def handle_oauth_authorize(request: web.Request) -> web.Response:
    provider_name = request.match_info.get("provider", "")
    provider = _provider_for(provider_name)
    if provider is None:
        return web.json_response(
            {
                "error": "oauth_not_configured",
                "message": (
                    f"OAuth for '{provider_name}' is not configured. "
                    f"Set {provider_name.upper()}_CLIENT_ID and "
                    f"{provider_name.upper()}_CLIENT_SECRET."
                ),
            },
            status=400,
        )

    _cleanup_state()
    state = secrets.token_urlsafe(24)
    redirect_uri = _redirect_base(request)
    _OAUTH_STATE[state] = {
        "provider": provider_name,
        "redirect_uri": redirect_uri,
        "created": time.time(),
    }
    url = provider.get_authorization_url(state=state, redirect_uri=redirect_uri)
    raise web.HTTPFound(url)


async def handle_oauth_callback(request: web.Request) -> web.Response:
    error = request.query.get("error")
    if error:
        return web.Response(
            text=f"<html><body><h1>OAuth failed</h1><p>{error}</p>"
            "<p><a href='/credentials'>Back to credentials</a></body></html>",
            content_type="text/html",
            status=400,
        )

    code = request.query.get("code")
    state = request.query.get("state")
    if not code or not state or state not in _OAUTH_STATE:
        return web.Response(text="Invalid OAuth state", status=400)

    meta = _OAUTH_STATE.pop(state)
    provider_name = meta["provider"]
    provider = _provider_for(provider_name)
    if provider is None:
        return web.Response(text="OAuth provider unavailable", status=400)

    redirect_uri = meta["redirect_uri"]
    token_obj = provider.exchange_code(code, redirect_uri=redirect_uri)
    access_token = getattr(token_obj, "access_token", None) or (
        token_obj.get("access_token") if isinstance(token_obj, dict) else None
    )
    refresh = getattr(token_obj, "refresh_token", None) or (
        token_obj.get("refresh_token") if isinstance(token_obj, dict) else None
    )
    if not access_token:
        return web.Response(text="Token exchange did not return access_token", status=400)

    store = _store(request)
    cred_id = provider_name if provider_name != "google" else "google_calendar"
    keys = {"access_token": CredentialKey(name="access_token", value=SecretStr(access_token))}
    if refresh:
        keys["refresh_token"] = CredentialKey(name="refresh_token", value=SecretStr(refresh))
    store.save_credential(CredentialObject(id=cred_id, keys=keys))

    env_map = {
        "hubspot": "HUBSPOT_ACCESS_TOKEN",
        "zoho": "ZOHO_ACCESS_TOKEN",
        "google_calendar": "GOOGLE_CALENDAR_ACCESS_TOKEN",
        "google": "GOOGLE_CALENDAR_ACCESS_TOKEN",
    }
    env_var = env_map.get(provider_name)
    if env_var:
        os.environ[env_var] = access_token

    return web.Response(
        text=(
            "<html><body><h1>Connected</h1>"
            f"<p>{provider_name.title()} credentials saved.</p>"
            "<p><a href='/credentials'>Back to credentials</a></body></html>"
        ),
        content_type="text/html",
    )


def register_routes(app: web.Application) -> None:
    app.router.add_get("/api/oauth/{provider}/authorize", handle_oauth_authorize)
    app.router.add_get("/api/oauth/callback", handle_oauth_callback)
