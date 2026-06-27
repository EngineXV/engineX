# Engine Architecture

## Overview

Engine is a goal-driven agent runtime. Agents are declarative Python modules that export a `goal`, `nodes`, and `edges`. The CLI loads an agent, wires LLM + MCP tools + credentials, and runs it through a concurrent event-driven runtime.

## Package layout

```
core/engine/
├── graph/           # Agent graph model and execution
│   ├── goal.py      # Goals, success criteria, constraints
│   ├── node.py      # NodeSpec, NodeProtocol, NodeContext
│   ├── edge.py      # GraphSpec, EdgeSpec, routing conditions
│   ├── executor.py  # GraphExecutor — parallel fan-out, retries, HITL
│   └── event_loop/  # EventLoopNode — multi-turn LLM + tools + judge
├── runtime/         # Orchestration layer
│   ├── agent_runtime.py    # Multi-entry-point concurrent runtime
│   ├── execution_stream.py # Per-stream graph execution
│   └── event_bus.py        # Pub/sub for TUI and observability
├── runner/          # CLI integration
│   ├── runner.py            # AgentRunner — load, setup, run
│   ├── loader.py            # Agent export parsing
│   ├── subscription_auth.py # Claude Code / Codex OAuth tokens
│   └── tool_registry.py     # MCP + local tool discovery
├── credentials/     # Encrypted credential store, OAuth, validation
├── llm/             # LLMProvider ABC + LiteLLM / Anthropic / Mock
├── storage/         # Session state, checkpoints (filesystem JSON)
├── observability/   # Run history, metrics, optional OTEL
├── server/          # Dashboard API (sessions, OAuth, checkpoints, ops)
├── skills/          # SKILL.md discovery + runtime injection
└── tui/             # Textual terminal dashboard
tools/               # MCP data tools (engine_tools)
```

## Execution flow

```
./engine run <agent>
    → AgentRunner.load()
    → preload validation (graph + credentials)
    → ToolRegistry (MCP servers, local tools)
    → AgentRuntime.start()
    → ExecutionStream → GraphExecutor → EventLoopNode
    → EventBus → TUI / logs
```

## Key concepts

| Concept | Description |
|---------|-------------|
| **Goal** | North star with weighted success criteria and hard/soft constraints |
| **Node** | Unit of work (`event_loop`, client-facing HITL, etc.) |
| **Edge** | Routing: `ON_SUCCESS`, `CONDITIONAL` (safe_eval), `LLM_DECIDE` |
| **Event loop node** | Multi-turn LLM loop with synthetic tools (`set_output`, `ask_user`), judge, compaction |
| **AgentRuntime** | Manages concurrent execution streams and shared state |
| **Checkpoint** | Persist/resume session state at node boundaries |

## Configuration

| Location | Purpose |
|----------|---------|
| `~/.engine/configuration.json` | Default LLM provider/model |
| `~/.engine/credentials/` | Encrypted API keys |
| `.env` | Environment API keys (optional) |
| `ENGINE_DATA_ROOT` | Sandbox root for MCP data tools |

## Extending

- **New agent**: add `agent.py` with `goal`, `nodes`, `edges` under `examples/templates/`
- **New LLM**: use LiteLLM model string (`ollama/qwen2.5:7b`, `anthropic/...`)
- **New tools**: `tools.py` in agent dir, or `mcp_servers.json` for MCP
- **New credential**: register in credential store + validation

## Testing

```bash
make check    # ruff lint + format
make test     # core pytest suite
cd tools && uv run pytest tests/ -q
```

CI runs lint, tests, example agent validation, and coverage reporting.
