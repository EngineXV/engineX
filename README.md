# Engine

Minimal goal-driven agent runtime — graphs, event-loop nodes, human-in-the-loop, checkpoints, credentials, CLI.

## Quick start

```bash
uv sync
./engine validate examples/templates/contract_review
./engine run examples/templates/contract_review --tui
```

## What's included

| Path | Purpose |
|------|---------|
| `core/framework/` | Runtime: goals, graphs, HITL, executor, storage, TUI, CLI |
| `tools/` | File data tools + credential helpers (`load_data`, `save_data`, …) |
| `examples/templates/contract_review/` | HITL contract review agent (no external tools) |

## Commands

```bash
./engine run <agent> --input '{...}'
./engine validate <agent>
./engine tui
./engine shell <agent>
```

Config and encrypted credentials: `~/.engine/`
