"""HTTP routes for the Engine skills library."""

from __future__ import annotations

import io
import logging
import re
import zipfile
from pathlib import Path

from aiohttp import web

from engine.skills.discovery import SKILL_FILENAME, discover_skills, read_skill_body

logger = logging.getLogger(__name__)

_MAX_UPLOAD_BYTES = 2 * 1024 * 1024
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


async def handle_list_skills(request: web.Request) -> web.Response:
    repo_root = request.app["repo_root"]
    skills = [entry.to_row() for entry in discover_skills(repo_root)]
    return web.json_response({"skills": skills, "count": len(skills)})


async def handle_get_skill(request: web.Request) -> web.Response:
    name = request.match_info["skill_name"]
    repo_root = request.app["repo_root"]
    result = read_skill_body(name, repo_root)
    if result is None:
        return web.json_response({"error": f"Skill '{name}' not found"}, status=404)
    entry, body, files = result
    return web.json_response(
        {
            **entry.to_row(),
            "body": body,
            "files": files,
        }
    )


async def handle_delete_skill(request: web.Request) -> web.Response:
    name = request.match_info["skill_name"]
    target = Path.home() / ".engine" / "skills" / name
    if not target.is_dir():
        return web.json_response({"error": f"Skill '{name}' not found"}, status=404)
    import shutil

    shutil.rmtree(target)
    return web.json_response({"deleted": True, "name": name})


async def handle_upload_skill(request: web.Request) -> web.Response:
    reader = await request.multipart()
    field = await reader.next()
    if field is None or field.name != "file":
        return web.json_response({"error": "Expected multipart field 'file'"}, status=400)

    raw = await field.read(decode=False)
    if len(raw) > _MAX_UPLOAD_BYTES:
        return web.json_response({"error": "File too large (max 2MB)"}, status=413)

    skill_name = request.query.get("name", "").strip()
    user_dir = Path.home() / ".engine" / "skills"
    user_dir.mkdir(parents=True, exist_ok=True)

    if raw[:4] == b"PK\x03\x04":
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            for info in zf.infolist():
                if info.filename.endswith(SKILL_FILENAME):
                    content = zf.read(info)
                    folder = Path(info.filename).parent.name or skill_name
                    if not skill_name:
                        skill_name = folder
                    break
            else:
                return web.json_response({"error": "ZIP must contain a SKILL.md file"}, status=400)
    else:
        content = raw
        if not skill_name:
            return web.json_response(
                {"error": "Query param 'name' required for .md upload"},
                status=400,
            )

    if not _NAME_RE.match(skill_name):
        return web.json_response({"error": "Invalid skill name"}, status=400)

    dest = user_dir / skill_name
    dest.mkdir(parents=True, exist_ok=True)
    (dest / SKILL_FILENAME).write_bytes(content)
    return web.json_response({"uploaded": skill_name, "path": str(dest)}, status=201)


def register_routes(app: web.Application) -> None:
    app.router.add_get("/api/skills", handle_list_skills)
    app.router.add_get("/api/skills/{skill_name}", handle_get_skill)
    app.router.add_delete("/api/skills/{skill_name}", handle_delete_skill)
    app.router.add_post("/api/skills/upload", handle_upload_skill)
