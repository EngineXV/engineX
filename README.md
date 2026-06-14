# Engine

Minimal goal-driven agent runtime — graphs, event-loop nodes, human-in-the-loop, checkpoints, credentials, CLI.

## Quick start

```bash
uv sync
./engine validate examples/templates/contract_review
./engine run examples/templates/contract_review --tui
```

## Layout

```
engine/
├── engine              # CLI wrapper script
├── core/engine/        # Runtime package (import: engine)
├── tools/              # MCP data tools (import: engine_tools)
└── examples/templates/contract_review/
```

## Commands

```bash
./engine run <agent> [--tui] [--input '{...}']
./engine validate <agent>
./engine info <agent>
./engine tui
./engine shell <agent>
./engine setup-credentials <agent>
```

Config and credentials: `~/.engine/`
