# Integration Examples

EngineX ships credential specs for common connectors. Wire MCP servers in each agent's `mcp_servers.json`.

## Slack (log_monitor alerts)

Set `SLACK_BOT_TOKEN` in Credentials or `.env`. Used by the log monitor template for alert dispatch.

## HubSpot / Zoho CRM

1. Set `HUBSPOT_CLIENT_ID` + `HUBSPOT_CLIENT_SECRET` (or Zoho equivalents).
2. Open **Credentials** in the dashboard and click **Connect with OAuth**.
3. Tokens are stored in `~/.engine/credentials`.

## Google Calendar (meeting_scheduler)

Add your Calendar MCP server to `examples/templates/meeting_scheduler/mcp_servers.json` and set `GOOGLE_CALENDAR_ACCESS_TOKEN` or your OAuth flow.

Example shape:

```json
{
  "servers": [
    {
      "name": "calendar",
      "transport": "stdio",
      "command": "uv",
      "args": ["run", "your-calendar-mcp-server"],
      "cwd": "."
    }
  ]
}
```
