# Core

Python package `framework` — graph runtime, CLI, TUI, credentials, checkpoints.

## Setup

```bash
uv sync
uv run --project core python -m pytest core/tests/ -q
```

Entry point: `./engine` → `framework.cli:main`

Agent templates: `examples/templates/`. User agents: `exports/` (gitignored).
