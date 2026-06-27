"""Ops console API routes."""

from __future__ import annotations

from aiohttp import web

from engine.observability.metrics import prometheus_text, snapshot
from engine.observability.otel import configure_otel_if_enabled
from engine.observability.run_history import collect_alerts, collect_run_history


def _repo_root(request: web.Request):
    return request.app["repo_root"]


async def handle_ops_summary(_request: web.Request) -> web.Response:
    otel = configure_otel_if_enabled()
    return web.json_response(
        {
            "metrics": snapshot(),
            "otel": otel,
        }
    )


async def handle_ops_runs(request: web.Request) -> web.Response:
    limit = int(request.query.get("limit", "50"))
    runs = collect_run_history(_repo_root(request), limit=limit)
    return web.json_response({"runs": runs, "count": len(runs)})


async def handle_ops_alerts(request: web.Request) -> web.Response:
    limit = int(request.query.get("limit", "20"))
    alerts = collect_alerts(_repo_root(request), limit=limit)
    return web.json_response({"alerts": alerts, "count": len(alerts)})


async def handle_ops_metrics_export(_request: web.Request) -> web.Response:
    return web.Response(text=prometheus_text(), content_type="text/plain; version=0.0.4")


def register_routes(app: web.Application) -> None:
    app.router.add_get("/api/ops/summary", handle_ops_summary)
    app.router.add_get("/api/ops/runs", handle_ops_runs)
    app.router.add_get("/api/ops/alerts", handle_ops_alerts)
    app.router.add_get("/api/ops/metrics", handle_ops_metrics_export)
