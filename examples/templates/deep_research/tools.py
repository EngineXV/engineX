"""Tools for Deep Research agent — search, scrape, and report file helpers."""

from __future__ import annotations

import html
import os
import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

import httpx

from engine.runner.tool_registry import tool

try:
    from engine_tools.tools.data_tools import _open_file_uri, _resolve_data_dir
except ImportError:  # pragma: no cover - engine_tools optional in some test contexts

    def _resolve_data_dir(data_dir: str) -> tuple[Any, str | None]:
        return None, "data_dir support unavailable"

    def _open_file_uri(file_uri: str) -> tuple[bool, str]:
        return False, "Browser open unavailable"


_DEMO_RESULTS: dict[str, list[dict[str, str]]] = {
    "default": [
        {
            "title": "Overview — Wikipedia",
            "url": "https://en.wikipedia.org/wiki/Main_Page",
            "snippet": "Encyclopedic summary and background on the topic.",
        },
        {
            "title": "Recent analysis — Reuters",
            "url": "https://www.reuters.com/",
            "snippet": "News coverage and current developments.",
        },
        {
            "title": "Technical deep dive — arXiv",
            "url": "https://arxiv.org/",
            "snippet": "Research papers and technical references.",
        },
    ]
}


def _brave_api_key() -> str | None:
    env_key = os.environ.get("BRAVE_SEARCH_API_KEY")
    if env_key:
        return env_key
    try:
        from engine.credentials.store import CredentialStore

        return CredentialStore().get("brave_search")
    except Exception:
        return None


def _demo_search(query: str) -> dict[str, Any]:
    results = _DEMO_RESULTS.get("default", [])
    return {
        "query": query,
        "results": [{**item, "query": query} for item in results],
        "source": "demo",
        "note": "Set BRAVE_SEARCH_API_KEY or brave_search credential for live search.",
    }


@tool(
    description="Search the web for a query (Brave API when configured, else demo results)."
)
def web_search(query: str, count: int = 5) -> dict[str, Any]:
    api_key = _brave_api_key()
    if not api_key:
        return _demo_search(query)

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": api_key},
                params={"q": query, "count": str(min(max(count, 1), 10))},
            )
        if response.status_code != 200:
            return {**_demo_search(query), "api_error": response.status_code}
        payload = response.json()
        web = payload.get("web", {})
        results = [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("description", ""),
            }
            for item in web.get("results", [])[:count]
        ]
        return {"query": query, "results": results, "source": "brave"}
    except Exception as exc:
        return {**_demo_search(query), "error": str(exc)}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            text = data.strip()
            if text:
                self._chunks.append(text)

    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self._chunks)).strip()


@tool(description="Fetch a URL and return extracted page text.")
def web_scrape(url: str, max_chars: int = 12000) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return {"error": "Only http/https URLs are supported"}

    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            response = client.get(
                url,
                headers={"User-Agent": "EngineDeepResearch/1.0"},
            )
        if response.status_code >= 400:
            return {"error": f"HTTP {response.status_code}", "url": url}

        content_type = response.headers.get("content-type", "")
        body = response.text
        if "html" in content_type or "<html" in body[:500].lower():
            parser = _TextExtractor()
            parser.feed(body)
            text = parser.text()
        else:
            text = body

        text = html.unescape(text)[:max_chars]
        return {
            "url": url,
            "title": _title_from_html(body)
            if "<title" in body.lower()
            else parsed.netloc,
            "content": text,
            "chars": len(text),
        }
    except Exception as exc:
        return {"error": str(exc), "url": url}


def _title_from_html(body: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return html.unescape(re.sub(r"\s+", " ", match.group(1))).strip()


@tool(description="Save text content to a file in the agent data directory.")
def save_data(filename: str, data: str, data_dir: str) -> dict[str, Any]:
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        return {"error": "Invalid filename"}
    dir_path, err = _resolve_data_dir(data_dir)
    if err:
        return {"error": err}
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        path = dir_path / filename
        path.write_text(data, encoding="utf-8")
        return {
            "success": True,
            "filename": filename,
            "size_bytes": len(data.encode("utf-8")),
        }
    except Exception as exc:
        return {"error": str(exc)}


@tool(description="Append text to a file in the agent data directory.")
def append_data(filename: str, data: str, data_dir: str) -> dict[str, Any]:
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        return {"error": "Invalid filename"}
    dir_path, err = _resolve_data_dir(data_dir)
    if err:
        return {"error": err}
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        path = dir_path / filename
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(data)
        return {
            "success": True,
            "filename": filename,
            "appended_bytes": len(data.encode("utf-8")),
        }
    except Exception as exc:
        return {"error": str(exc)}


@tool(description="Load a slice of a file from the agent data directory.")
def load_data(
    filename: str,
    data_dir: str,
    offset_bytes: int = 0,
    limit_bytes: int = 10000,
) -> dict[str, Any]:
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        return {"error": "Invalid filename"}
    dir_path, err = _resolve_data_dir(data_dir)
    if err:
        return {"error": err}
    try:
        path = dir_path / filename
        if not path.exists():
            return {"error": f"File not found: {filename}"}
        raw = path.read_bytes()
        chunk = raw[offset_bytes : offset_bytes + limit_bytes]
        text = chunk.decode("utf-8", errors="replace")
        next_offset = offset_bytes + len(chunk)
        return {
            "success": True,
            "filename": filename,
            "content": text,
            "offset_bytes": offset_bytes,
            "next_offset_bytes": next_offset,
            "has_more": next_offset < len(raw),
        }
    except Exception as exc:
        return {"error": str(exc)}


@tool(description="List files in the agent data directory.")
def list_data_files(data_dir: str) -> dict[str, Any]:
    dir_path, err = _resolve_data_dir(data_dir)
    if err:
        return {"error": err}
    try:
        if not dir_path.exists():
            return {"files": []}
        files = [
            {"filename": item.name, "size_bytes": item.stat().st_size}
            for item in sorted(dir_path.iterdir())
            if item.is_file()
        ]
        return {"files": files}
    except Exception as exc:
        return {"error": str(exc)}


@tool(description="Return a file URI for the user (optionally open in browser).")
def serve_file_to_user(
    filename: str,
    data_dir: str,
    label: str = "",
    open_in_browser: bool = False,
) -> dict[str, Any]:
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        return {"error": "Invalid filename"}
    dir_path, err = _resolve_data_dir(data_dir)
    if err:
        return {"error": err}
    try:
        path = dir_path / filename
        if not path.exists():
            return {"error": f"File not found: {filename}"}
        full_path = str(path.resolve())
        file_uri = f"file://{full_path}"
        result: dict[str, Any] = {
            "success": True,
            "file_uri": file_uri,
            "file_path": full_path,
            "label": label or filename,
        }
        if open_in_browser:
            opened, message = _open_file_uri(file_uri)
            result["browser_opened"] = opened
            result["browser_message"] = message
        return result
    except Exception as exc:
        return {"error": str(exc)}
