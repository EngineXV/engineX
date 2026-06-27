# Meeting Scheduler

Find available calendar slots, book meetings with Google Meet, log to Google Sheets, and email confirmations.

## Flow

```
intake → schedule → confirm ──(another)──→ intake
                      └──(done)──→ end session
```

| Node | Type | Purpose |
|------|------|---------|
| intake | client-facing | Collect attendee, duration, and title |
| schedule | LLM + tools | Check calendar, create event, log sheet, send email |
| confirm | client-facing | Show booking summary; offer another meeting |

## Prerequisites

Configure Google OAuth credentials for Calendar, Sheets, and Gmail before running with live tools:

```bash
./engine credentials setup
```

The schedule node expects integration tools: `calendar_check_availability`, `calendar_create_event`, `calendar_list_events`, `google_sheets_*`, and `send_email`. Wire them via `mcp_servers.json` when your integration MCP server is available.

## Run

```bash
./engine validate examples/templates/meeting_scheduler
./engine run examples/templates/meeting_scheduler --tui
```

Headless (prefill meeting details):

```bash
./engine run examples/templates/meeting_scheduler \
  --input '{"attendee_email": "colleague@example.com", "meeting_duration_minutes": "30", "meeting_title": "Sync"}'
```

## Build your product on top

Wrap this agent in your scheduling API: user submits meeting request → engine books via Google Calendar → return Meet link and sheet row from `confirm` outputs.
