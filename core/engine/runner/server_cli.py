"""CLI helpers for the Engine HTTP server."""

from __future__ import annotations

import argparse
import asyncio
import shutil
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def _frontend_dir() -> Path | None:
    for candidate in (_repo_root() / "core" / "frontend", _repo_root() / "frontend"):
        if (candidate / "package.json").is_file():
            return candidate.resolve()
    return None


def _frontend_dist_exists() -> bool:
    frontend = _frontend_dir()
    return frontend is not None and (frontend / "dist" / "index.html").exists()


def _build_frontend() -> bool:
    frontend_dir = _frontend_dir()
    if frontend_dir is None:
        return False

    dist_dir = frontend_dir / "dist"
    src_dir = frontend_dir / "src"
    index_html = dist_dir / "index.html"
    if index_html.exists() and src_dir.is_dir():
        dist_mtime = index_html.stat().st_mtime
        needs_build = any(
            f.is_file() and f.stat().st_mtime > dist_mtime for f in src_dir.rglob("*")
        )
        if not needs_build:
            return True

    print("Building frontend...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    try:
        for cache_file in frontend_dir.glob("tsconfig*.tsbuildinfo"):
            cache_file.unlink(missing_ok=True)
        subprocess.run(
            [npm_cmd, "install", "--no-fund", "--no-audit"],
            cwd=frontend_dir,
            check=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        subprocess.run(
            [npm_cmd, "run", "build"],
            cwd=frontend_dir,
            check=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        print("Frontend built.")
        return True
    except FileNotFoundError:
        print("Node.js not found — skipping frontend build.")
        return index_html.exists()
    except subprocess.CalledProcessError as exc:
        output = (exc.stderr or exc.stdout or "").strip()
        if output:
            print(output[-2000:])
        print("Frontend build failed — API will still start.")
        return index_html.exists()


def _open_browser(url: str) -> None:
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif sys.platform == "win32":
            subprocess.Popen(
                ["cmd", "/c", "start", "", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            chrome = shutil.which("google-chrome") or shutil.which("chromium")
            if chrome:
                subprocess.Popen(
                    [chrome, url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    ["xdg-open", url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
    except Exception:
        pass


def cmd_serve(args: argparse.Namespace) -> int:
    try:
        from aiohttp import web
    except ImportError:
        print("Missing dependency: aiohttp")
        print("Install with: cd core && uv sync --extra server")
        return 1

    import signal

    from engine.observability import configure_logging
    from engine.server.app import create_app
    from engine.server.discovery import resolve_agent_path

    _build_frontend()
    configure_logging(level="DEBUG" if getattr(args, "debug", False) else "INFO")

    model = getattr(args, "model", None)
    app = create_app(model=model)
    repo_root = _repo_root()

    async def run_server() -> None:
        manager = app["manager"]
        shutdown_event = asyncio.Event()
        signal_count = {"n": 0}

        def _request_shutdown(signame: str) -> None:
            signal_count["n"] += 1
            if signal_count["n"] == 1:
                print(f"\nReceived {signame}, shutting down… (Ctrl+C again to force quit)")
                shutdown_event.set()

        loop = asyncio.get_running_loop()
        for signame in ("SIGINT", "SIGTERM"):
            try:
                loop.add_signal_handler(getattr(signal, signame), _request_shutdown, signame)
            except (NotImplementedError, AttributeError):
                pass

        for agent_arg in getattr(args, "agent", []) or []:
            resolved = resolve_agent_path(repo_root, agent_arg)
            if resolved is None:
                print(f"Agent not found: {agent_arg}")
                continue
            try:
                session = await manager.create_session(resolved, model=model)
                print(f"Loaded agent: {resolved.name} → session {session.id}")
            except Exception as exc:  # noqa: BLE001
                print(f"Error loading agent {agent_arg}: {exc}")

        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, args.host, args.port)
        await site.start()

        dashboard_url = f"http://{args.host}:{args.port}"
        has_frontend = _frontend_dist_exists()
        print()
        print(f"Engine API server running on {dashboard_url}")
        if has_frontend:
            print(f"Dashboard:  {dashboard_url}")
        print(f"Health:     {dashboard_url}/api/health")
        print(f"Sessions:   {len(manager.list_sessions())}")
        print()
        print("Press Ctrl+C to stop")

        if getattr(args, "open", False) and has_frontend:
            _open_browser(dashboard_url)

        try:
            await shutdown_event.wait()
        finally:
            await manager.shutdown_all()
            await runner.cleanup()

    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except OSError as exc:
        if exc.errno == 48:
            print(f"\nError: port {args.port} is already in use.", file=sys.stderr)
            print("Stop the other process or pick a different port:", file=sys.stderr)
            print(f"  ./engine open --port {args.port + 1}", file=sys.stderr)
            return 1
        raise
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    args.open = True
    return cmd_serve(args)
