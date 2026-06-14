# Engine Tools

Minimal MCP file/data tools for Engine agents.

## Tools

| Group | Tools |
|-------|-------|
| Data files | `load_data`, `save_data`, `append_data`, `list_data_files`, `serve_file_to_user`, `edit_data` |
| Utility | `get_current_timestamp` |

## MCP server

```bash
cd tools
uv run python files_server.py --stdio
```

Point agents at it via `mcp_servers.json`.
