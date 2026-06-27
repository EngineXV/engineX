"""Unified browser automation — extension first, Playwright fallback."""

from __future__ import annotations

from . import playwright_backend as pw
from .bridge import get_bridge


def extension_connected() -> bool:
    bridge = get_bridge()
    return bool(bridge and bridge.is_connected)


def backend_mode() -> str:
    if extension_connected():
        return "extension"
    if pw.playwright_available():
        return "playwright"
    return "none"
