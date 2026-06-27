# Deep Research

Interactive research workflow: **intake → research → review (HITL) → report**.

## Flow

```text
intake → research → review ──needs more──► research
                      │
                      └── satisfied ──► report ──► intake (new topic)
                                           └──► research (deeper)
```

- **review** and **report** are `pause_nodes` — approvers interact via the web dashboard.
- **research** uses `web_search` / `web_scrape` (Brave API when configured; demo results otherwise).
- **report** builds a cited HTML file via `save_data` / `append_data` and serves it to the user.

## Run

```bash
./engine validate examples/templates/deep_research
./engine run examples/templates/deep_research --tui
./engine serve   # dashboard HITL at http://127.0.0.1:8787
```

Optional: set `BRAVE_SEARCH_API_KEY` or configure `brave_search` credentials for live web search.
