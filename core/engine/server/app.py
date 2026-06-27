"""aiohttp application factory for the Engine dashboard."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from aiohttp import web

from engine.server.routes import register_routes
from engine.server.routes_credentials import register_routes as register_credential_routes
from engine.server.routes_skills import register_routes as register_skills_routes
from engine.server.routes_tasks import register_routes as register_task_routes
from engine.server.session import SessionManager

logger = logging.getLogger(__name__)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def _build_credential_store():
    from engine.credentials.storage import CompositeStorage, EncryptedFileStorage, EnvVarStorage
    from engine.credentials.store import CredentialStore
    from engine.credentials.validation import ensure_credential_key_env

    ensure_credential_key_env()
    try:
        from engine_tools.credentials import CREDENTIAL_SPECS
    except ImportError:
        return CredentialStore.for_testing({})

    env_mapping = {
        (spec.credential_id or name): spec.env_var for name, spec in CREDENTIAL_SPECS.items()
    }
    env_storage = EnvVarStorage(env_mapping=env_mapping)
    if os.environ.get("ENGINE_CREDENTIAL_KEY"):
        storage = CompositeStorage(primary=env_storage, fallbacks=[EncryptedFileStorage()])
    else:
        storage = env_storage
    return CredentialStore(storage=storage)


def create_app(*, model: str | None = None) -> web.Application:
    root = repo_root()
    manager = SessionManager(repo_root=root, default_model=model)
    app = web.Application()
    app["manager"] = manager
    app["repo_root"] = root
    app["default_model"] = model
    app["credential_store"] = _build_credential_store()
    register_routes(app)
    register_credential_routes(app)
    register_skills_routes(app)
    register_task_routes(app)
    _setup_static_serving(app)
    return app


def _setup_static_serving(app: web.Application) -> None:
    """Serve frontend static files when core/frontend/dist exists."""
    here = Path(__file__).resolve().parent  # core/engine/server
    candidates = [
        Path("core/frontend/dist"),
        Path("frontend/dist"),
        here.parent.parent / "frontend" / "dist",
    ]

    dist_dir: Path | None = None
    for candidate in candidates:
        if candidate.is_dir() and (candidate / "index.html").exists():
            dist_dir = candidate.resolve()
            break

    if dist_dir is None:
        logger.debug("No frontend/dist found — API-only mode")
        return

    logger.info("Serving frontend from %s", dist_dir)

    async def handle_spa(request: web.Request) -> web.FileResponse | web.Response:
        rel = request.match_info.get("path", "")
        if rel:
            file_path = (dist_dir / rel).resolve()
            try:
                file_path.relative_to(dist_dir)
            except ValueError:
                return web.Response(status=403)
            if file_path.is_file():
                return web.FileResponse(file_path)
        return web.FileResponse(dist_dir / "index.html")

    app.router.add_get("/", lambda r: web.FileResponse(dist_dir / "index.html"))
    app.router.add_static("/assets/", dist_dir / "assets", show_index=False)
    app.router.add_get(r"/{path:(?!api/).*}", handle_spa)
