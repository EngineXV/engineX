"""End-to-end tests for the Engine HTTP dashboard API and SPA serving."""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

import pytest
import pytest_asyncio
from aiohttp.test_utils import TestClient, TestServer

from engine.server.app import create_app


def _frontend_dist_exists() -> bool:
    root = Path(__file__).resolve().parents[2]
    dist = root / "frontend" / "dist" / "index.html"
    return dist.is_file()


def _ci_safe_agent_path(discover: dict) -> str:
    """Prefer templates that skip credential validation (stable in CI without API keys)."""
    templates = discover.get("templates", [])
    for entry in templates:
        path = entry.get("path", "")
        if "log_monitor" in path:
            return path
    for entry in templates:
        path = entry.get("path", "")
        if "meeting_scheduler" in path:
            return path
    for entry in templates:
        path = entry.get("path", "")
        if "agreement_analysis" in path:
            return path
    if not templates:
        raise AssertionError("No templates discovered")
    return templates[0]["path"]


@pytest_asyncio.fixture
async def client():
    app = create_app()
    server = TestServer(app)
    test_client = TestClient(server)
    await test_client.start_server()
    yield test_client
    await test_client.close()


@pytest.mark.asyncio
async def test_health(client: TestClient):
    resp = await client.get("/api/health")
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_config(client: TestClient):
    resp = await client.get("/api/config")
    assert resp.status == 200
    data = await resp.json()
    assert "model" in data


@pytest.mark.asyncio
async def test_discover_agents(client: TestClient):
    resp = await client.get("/api/discover")
    assert resp.status == 200
    data = await resp.json()
    templates = data.get("templates", [])
    assert any("agreement_analysis" in a.get("path", "") for a in templates)


@pytest.mark.asyncio
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
async def test_session_lifecycle(client: TestClient):
    discover = await (await client.get("/api/discover")).json()
    agent_path = _ci_safe_agent_path(discover)

    create = await client.post(
        "/api/sessions",
        json={"agent_path": agent_path},
    )
    assert create.status == 201, await create.text()
    session = await create.json()
    session_id = session["session_id"]
    assert session["name"]
    assert session_id

    detail = await client.get(f"/api/sessions/{session_id}")
    assert detail.status == 200
    body = await detail.json()
    assert body["session_id"] == session_id
    assert len(body.get("nodes", [])) > 0
    assert len(body.get("entry_points", [])) > 0

    listed = await (await client.get("/api/sessions")).json()
    assert any(s["session_id"] == session_id for s in listed["sessions"])

    deleted = await client.delete(f"/api/sessions/{session_id}")
    assert deleted.status == 200
    assert (await deleted.json())["stopped"] is True

    missing = await client.get(f"/api/sessions/{session_id}")
    assert missing.status == 404


@pytest.mark.asyncio
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
async def test_session_message_empty_rejected(client: TestClient):
    discover = await (await client.get("/api/discover")).json()
    agent_path = _ci_safe_agent_path(discover)
    create = await client.post("/api/sessions", json={"agent_path": agent_path})
    assert create.status == 201, await create.text()
    session = await create.json()
    session_id = session["session_id"]

    try:
        resp = await client.post(f"/api/sessions/{session_id}/message", json={"message": "   "})
        assert resp.status == 400
    finally:
        await client.delete(f"/api/sessions/{session_id}")


@pytest.mark.asyncio
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
async def test_session_sse_stream(client: TestClient):
    discover = await (await client.get("/api/discover")).json()
    agent_path = _ci_safe_agent_path(discover)
    create = await client.post("/api/sessions", json={"agent_path": agent_path})
    assert create.status == 201, await create.text()
    session = await create.json()
    session_id = session["session_id"]

    try:
        resp = await client.get(f"/api/sessions/{session_id}/events")
        assert resp.status == 200
        assert resp.content_type.startswith("text/event-stream")

        # Read briefly — should get keepalive or stay open without error
        chunk = await asyncio.wait_for(resp.content.readany(), timeout=20.0)
        assert chunk is not None
    finally:
        resp.close()
        await client.delete(f"/api/sessions/{session_id}")


@pytest.mark.asyncio
async def test_credentials_specs(client: TestClient):
    resp = await client.get("/api/credentials/specs")
    assert resp.status == 200
    data = await resp.json()
    assert "specs" in data
    assert "has_engine_oauth_key" in data


@pytest.mark.asyncio
async def test_skills_list(client: TestClient):
    resp = await client.get("/api/skills")
    assert resp.status == 200
    data = await resp.json()
    assert "skills" in data
    assert "count" in data


@pytest.mark.asyncio
@pytest.mark.skipif(not _frontend_dist_exists(), reason="frontend dist not built")
async def test_spa_routes_serve_index(client: TestClient):
    for path in ("/", "/session/test-id", "/credentials", "/skills", "/org-chart"):
        resp = await client.get(path)
        assert resp.status == 200, path
        html = await resp.text()
        assert "Engine" in html
        assert "/assets/" in html


@pytest.mark.asyncio
@pytest.mark.skipif(not _frontend_dist_exists(), reason="frontend dist not built")
async def test_static_assets(client: TestClient):
    index = await (await client.get("/")).text()
    match = re.search(r'src="(/assets/[^"]+)"', index)
    assert match, "built index should reference /assets/"
    asset = await client.get(match.group(1))
    assert asset.status == 200
    assert len(await asset.read()) > 1000
