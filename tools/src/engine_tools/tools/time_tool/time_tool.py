"""Time Tool - Get current date and time for FastMCP"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fastmcp import FastMCP


def register_tools(mcp: FastMCP) -> None:
    """Register time tools with the MCP server"""

    @mcp.tool()
    def get_current_time(timezone: str = "UTC") -> dict:
        """Get the current date and time"""
        try:
            tz = ZoneInfo(timezone)
            now = datetime.now(tz)

            return {
                "datetime": now.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "timezone": timezone,
                "day_of_week": now.strftime("%A"),
                "unix_timestamp": int(now.timestamp()),
            }

        except KeyError:
            return {"error": f"Invalid timezone: {timezone}"}
