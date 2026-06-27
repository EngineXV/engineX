"""Credential CRUD routes for the Engine dashboard."""

from __future__ import annotations

import asyncio
import logging
import os

from aiohttp import web
from pydantic import SecretStr

from engine.credentials.models import CredentialDecryptionError, CredentialKey, CredentialObject
from engine.credentials.store import CredentialStore
from engine.server.discovery import resolve_agent_path

logger = logging.getLogger(__name__)


def _get_store(request: web.Request) -> CredentialStore:
    return request.app["credential_store"]


def _credential_to_dict(cred: CredentialObject) -> dict:
    return {
        "credential_id": cred.id,
        "credential_type": str(cred.credential_type),
        "key_names": list(cred.keys.keys()),
        "created_at": cred.created_at.isoformat() if cred.created_at else None,
        "updated_at": cred.updated_at.isoformat() if cred.updated_at else None,
    }


def _is_available(store: CredentialStore, credential_id: str) -> bool:
    try:
        return store.is_available(credential_id)
    except CredentialDecryptionError as exc:
        logger.warning("Credential '%s' unreadable: %s", credential_id, exc)
        return False


def _status_to_dict(c) -> dict:
    return {
        "credential_name": c.credential_name,
        "credential_id": c.credential_id,
        "env_var": c.env_var,
        "description": c.description,
        "help_url": c.help_url,
        "tools": c.tools,
        "node_types": c.node_types,
        "available": c.available,
        "direct_api_key_supported": c.direct_api_key_supported,
        "engine_oauth_supported": getattr(c, "engine_oauth_supported", False),
        "credential_key": c.credential_key,
        "valid": c.valid,
        "validation_message": c.validation_message,
        "alternative_group": getattr(c, "alternative_group", None),
    }


async def handle_list_credentials(request: web.Request) -> web.Response:
    store = _get_store(request)
    credentials = []
    unreadable = []
    for cid in store.list_credentials():
        try:
            cred = store.get_credential(cid, refresh_if_needed=False)
        except CredentialDecryptionError:
            unreadable.append(cid)
            continue
        if cred:
            credentials.append(_credential_to_dict(cred))
    return web.json_response({"credentials": credentials, "unreadable_credentials": unreadable})


async def handle_get_credential(request: web.Request) -> web.Response:
    credential_id = request.match_info["credential_id"]
    store = _get_store(request)
    try:
        cred = store.get_credential(credential_id, refresh_if_needed=False)
    except CredentialDecryptionError:
        return web.json_response(
            {"error": f"Credential '{credential_id}' could not be decrypted", "recoverable": True},
            status=409,
        )
    if cred is None:
        return web.json_response({"error": f"Credential '{credential_id}' not found"}, status=404)
    return web.json_response(_credential_to_dict(cred))


async def handle_save_credential(request: web.Request) -> web.Response:
    body = await request.json()
    credential_id = body.get("credential_id")
    keys = body.get("keys")
    if not credential_id or not keys or not isinstance(keys, dict):
        return web.json_response({"error": "credential_id and keys are required"}, status=400)

    store = _get_store(request)
    cred = CredentialObject(
        id=credential_id,
        keys={k: CredentialKey(name=k, value=SecretStr(v)) for k, v in keys.items()},
    )
    store.save_credential(cred)

    env_var = _env_var_for(credential_id)
    if env_var and keys.get("api_key"):
        os.environ[env_var] = keys["api_key"]

    return web.json_response({"saved": credential_id}, status=201)


async def handle_delete_credential(request: web.Request) -> web.Response:
    credential_id = request.match_info["credential_id"]
    store = _get_store(request)
    deleted = store.delete_credential(credential_id)
    env_var = _env_var_for(credential_id)
    if env_var:
        os.environ.pop(env_var, None)
    if not deleted and not env_var:
        return web.json_response({"error": f"Credential '{credential_id}' not found"}, status=404)
    return web.json_response({"deleted": True})


async def handle_check_agent(request: web.Request) -> web.Response:
    body = await request.json()
    agent_path = body.get("agent_path")
    verify = body.get("verify", True)
    if not agent_path:
        return web.json_response({"error": "agent_path is required"}, status=400)

    resolved = resolve_agent_path(request.app["repo_root"], agent_path)
    if resolved is None:
        return web.json_response({"error": f"Agent not found: {agent_path}"}, status=404)

    try:
        from engine.credentials.setup import load_agent_nodes
        from engine.credentials.validation import (
            ensure_credential_key_env,
            validate_agent_credentials,
        )

        ensure_credential_key_env()
        nodes = load_agent_nodes(resolved)
        result = validate_agent_credentials(
            nodes, verify=verify, raise_on_error=False, force_refresh=True
        )
        return web.json_response(
            {
                "required": [_status_to_dict(c) for c in result.credentials],
                "has_engine_oauth_key": getattr(result, "has_engine_sync_key", False),
            }
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error checking agent credentials: %s", exc)
        return web.json_response(
            {"error": "Internal server error while checking credentials"},
            status=500,
        )


async def handle_list_specs(request: web.Request) -> web.Response:
    try:
        from engine_tools.credentials import CREDENTIAL_SPECS

        from engine.credentials.storage import CompositeStorage, EncryptedFileStorage, EnvVarStorage
        from engine.credentials.validation import ensure_credential_key_env

        ensure_credential_key_env()
        env_mapping = {
            (spec.credential_id or name): spec.env_var for name, spec in CREDENTIAL_SPECS.items()
        }
        env_storage = EnvVarStorage(env_mapping=env_mapping)
        if os.environ.get("ENGINE_CREDENTIAL_KEY"):
            storage = CompositeStorage(primary=env_storage, fallbacks=[EncryptedFileStorage()])
        else:
            storage = env_storage
        store = CredentialStore(storage=storage)

        specs = []
        for name, spec in CREDENTIAL_SPECS.items():
            cred_id = spec.credential_id or name
            specs.append(
                {
                    "credential_name": name,
                    "credential_id": cred_id,
                    "env_var": spec.env_var,
                    "description": spec.description,
                    "help_url": spec.help_url,
                    "api_key_instructions": getattr(spec, "api_key_instructions", ""),
                    "tools": spec.tools,
                    "engine_oauth_supported": getattr(spec, "engine_oauth_supported", False),
                    "direct_api_key_supported": getattr(spec, "direct_api_key_supported", True),
                    "credential_key": spec.credential_key,
                    "credential_group": getattr(spec, "credential_group", ""),
                    "available": _is_available(store, cred_id),
                    "accounts": [],
                }
            )
        has_oauth_key = bool(os.environ.get("ENGINE_OAUTH_API_KEY"))
        return web.json_response({"specs": specs, "has_engine_oauth_key": has_oauth_key})
    except ImportError:
        has_oauth_key = bool(os.environ.get("ENGINE_OAUTH_API_KEY"))
        return web.json_response({"specs": [], "has_engine_oauth_key": has_oauth_key})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error listing credential specs: %s", exc)
        return web.json_response(
            {"error": "Internal server error while listing credential specs"},
            status=500,
        )


async def handle_validate_key(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    provider_id = body.get("provider_id", "").strip()
    api_key = body.get("api_key", "").strip()
    if not provider_id or not api_key:
        return web.json_response({"error": "provider_id and api_key are required"}, status=400)

    try:
        from engine_tools.credentials import CREDENTIAL_SPECS
        from engine_tools.credentials.health_check import check_credential_health

        spec = CREDENTIAL_SPECS.get(provider_id)
        if spec is None:
            return web.json_response({"valid": None, "message": f"Unknown provider: {provider_id}"})

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: check_credential_health(spec, api_key),
        )
        return web.json_response(
            {"valid": result.valid, "message": result.message or ""},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Key validation failed for %s: %s", provider_id, exc)
        return web.json_response({"valid": None, "message": f"Validation error: {exc}"})


async def handle_resync_credentials(_request: web.Request) -> web.Response:
    return web.json_response(
        {"error": "OAuth resync is not configured for Engine", "accounts_by_provider": {}},
        status=400,
    )


def _env_var_for(credential_id: str) -> str | None:
    try:
        from engine_tools.credentials import CREDENTIAL_SPECS

        for name, spec in CREDENTIAL_SPECS.items():
            if (spec.credential_id or name) == credential_id:
                return spec.env_var
    except ImportError:
        pass
    return None


def register_routes(app: web.Application) -> None:
    app.router.add_get("/api/credentials/specs", handle_list_specs)
    app.router.add_post("/api/credentials/check-agent", handle_check_agent)
    app.router.add_post("/api/credentials/resync", handle_resync_credentials)
    app.router.add_post("/api/credentials/validate-key", handle_validate_key)
    app.router.add_get("/api/credentials", handle_list_credentials)
    app.router.add_post("/api/credentials", handle_save_credential)
    app.router.add_get("/api/credentials/{credential_id}", handle_get_credential)
    app.router.add_delete("/api/credentials/{credential_id}", handle_delete_credential)
