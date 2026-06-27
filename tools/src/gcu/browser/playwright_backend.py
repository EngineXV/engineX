"""Headless Playwright fallback when the Chrome extension is unavailable."""

from __future__ import annotations

import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)

_playwright = None
_browser = None
_contexts: dict[str, dict[str, Any]] = {}
_tab_counter = 0


def playwright_available() -> bool:
    try:
        import playwright  # noqa: F401

        return True
    except ImportError:
        return False


async def _ensure_playwright() -> Any:
    global _playwright, _browser
    from playwright.async_api import async_playwright

    if _playwright is None:
        _playwright = await async_playwright().start()
    if _browser is None:
        _browser = await _playwright.chromium.launch(headless=True)
        logger.info("GCU Playwright fallback: launched headless Chromium")
    return _browser


async def shutdown_playwright() -> None:
    global _playwright, _browser
    _contexts.clear()
    if _browser is not None:
        await _browser.close()
        _browser = None
    if _playwright is not None:
        await _playwright.stop()
        _playwright = None


async def create_context(profile: str) -> dict[str, Any]:
    global _tab_counter
    browser = await _ensure_playwright()
    ctx = await browser.new_context()
    page = await ctx.new_page()
    _tab_counter += 1
    tab_id = _tab_counter
    _contexts[profile] = {
        "browser_context": ctx,
        "page": page,
        "activeTabId": tab_id,
        "tabs": {tab_id},
        "backend": "playwright",
    }
    return {"groupId": profile, "tabId": tab_id, "backend": "playwright"}


def get_context(profile: str) -> dict[str, Any] | None:
    return _contexts.get(profile)


async def navigate(
    profile: str,
    url: str,
    *,
    wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = "load",
) -> dict[str, Any]:
    ctx = _contexts.get(profile)
    if ctx is None:
        await create_context(profile)
        ctx = _contexts[profile]
    page = ctx["page"]
    await page.goto(url, wait_until=wait_until)
    return {"url": page.url, "title": await page.title()}


async def snapshot(profile: str) -> dict[str, Any]:
    ctx = _contexts.get(profile)
    if ctx is None:
        raise RuntimeError("No Playwright browser context")
    page = ctx["page"]
    text = await page.inner_text("body")
    return {"url": page.url, "title": await page.title(), "text": text[:12000]}


async def click(profile: str, selector: str) -> dict[str, Any]:
    ctx = _contexts.get(profile)
    if ctx is None:
        raise RuntimeError("No Playwright browser context")
    await ctx["page"].click(selector, timeout=8000)
    return {"ok": True, "selector": selector}


async def type_text(profile: str, selector: str, text: str) -> dict[str, Any]:
    ctx = _contexts.get(profile)
    if ctx is None:
        raise RuntimeError("No Playwright browser context")
    await ctx["page"].fill(selector, text, timeout=8000)
    return {"ok": True, "selector": selector}
