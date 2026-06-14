"""Engine Tools — file data tools and credentials for the agent runtime"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fastmcp import FastMCP

if TYPE_CHECKING:
    from engine_tools.credentials import CredentialStoreAdapter

from .data_tools import register_tools as register_data_tools
from .time_tool import register_tools as register_time


def register_all_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
    include_unverified: bool = False,
) -> list[str]:
    """Register minimal tools (data files + timestamp)"""
    del credentials, include_unverified
    register_data_tools(mcp)
    register_time(mcp)
    try:
        tools = asyncio.run(mcp.list_tools())
        return [t.name for t in tools]
    except Exception:
        return []


__all__ = ["register_all_tools"]
