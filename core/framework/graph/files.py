"""File tools MCP server constants"""

# ---------------------------------------------------------------------------
# MCP server identity
# ---------------------------------------------------------------------------

FILES_MCP_SERVER_NAME = "files-tools"
"""File tools MCP server name in mcp_servers.json."""

FILES_MCP_SERVER_CONFIG: dict = {
    "name": FILES_MCP_SERVER_NAME,
    "transport": "stdio",
    "command": "python",
    "args": ["files_server.py", "--stdio"],
    "cwd": "../../tools",
    "description": "File tools for reading, writing, editing, and searching files",
}
"""Default stdio config for the file tools MCP server."""
