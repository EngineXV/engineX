# EngineX

<img src="https://github.com/user-attachments/assets/756e0f11-30c2-46e2-a288-959652101084" alt="EngineX Banner" width="100%">

Open-source goal-driven agent runtime — workflow graphs, event-loop nodes, human-in-the-loop, checkpoints, credentials, MCP tools, CLI, and web dashboard.

## Introduction

EngineX is a framework for building and running **goal-driven agent workflows** in production. Define multi-step graphs (LLM steps, tools, validation loops, human approval gates), run them headless or via a web dashboard, and deploy in a client VPC with local credential storage.

**Typical uses:** document review with HITL, support triage, invoice validation, log monitoring, reconciliation, calendar/CRM automation, and custom client workflows built on the same runtime.

## Key Features

- **Workflow graphs** — nodes, edges, fan-out/fan-in, subagents, supervisors
- **Event-loop nodes** — LLM + tool calling with automatic output validation and retry
- **Human-in-the-loop (HITL)** — pause nodes, dashboard review, checkpoint resume
- **Checkpoints & session state** — fault tolerance; resume from paused steps
- **Credential vault** — encrypted local store (`~/.engine/credentials/`) + OAuth Connect
- **MCP tools** — Slack, browser automation, terminal, files, and custom `tools.py`
- **CLI & TUI** — `./engine run`, validate, setup-credentials, interactive terminal UI
- **Web dashboard** — sessions, graph view, HITL panels, ops console, credentials OAuth

## Quick Start

```bash
git clone https://github.com/EngineXV/engineX.git
cd engineX
./quickstart.sh    # uv sync + validate example agent
./engine run examples/templates/agreement_analysis --tui
```

Or manually:

```bash
uv sync
./engine validate examples/templates/agreement_analysis
./engine run examples/templates/agreement_analysis --tui
```

### Web Dashboard

```bash
cd core/frontend && npm install && npm run build
cd ../..
./engine serve
```

Open [http://127.0.0.1:8787](http://127.0.0.1:8787) for sessions, HITL review, checkpoints, credentials, and ops metrics.

## Workflow Templates

**15 reference templates** ship in `examples/templates/` — **8 workflow agents** + **7 department supervisors**. These are demos and accelerators; production client workflows typically live in `exports/` (gitignored) or a private repo.

See the full list: [examples/templates/README.md](examples/templates/README.md)

| Category | Templates |
|----------|-----------|
| **HITL review** | agreement_analysis, invoice_review, support_triage, medical_billing_auditor |
| **Automation** | log_monitor (daemon), hourly_tracking, meeting_scheduler, deep_research |
| **Supervisors** | technology, legal, finance, marketing, operations, growth, brand_design |
| **Composite** | supervised_agreement_analysis |

```bash
./engine validate examples/templates/log_monitor
./engine run examples/templates/medical_billing_auditor --tui
./engine run examples/templates/log_monitor --daemon --require-live
```

Integration patterns (Slack, HubSpot, Google Calendar): [examples/templates/integrations/README.md](examples/templates/integrations/README.md)

## Client Deployments

EngineX OSS is designed for **self-hosted installs in a client VPC**:

- One install = one isolated environment; data under `~/.engine/`
- Headless (`./engine run`, cron, systemd) and/or dashboard (`./engine serve`)
- Custom agents call client backend APIs via `tools.py` and accept JSON via `--input` / `--input-file`
- Client-specific agents are **not** committed to this public repo

See open INFO tickets for deployment and architecture notes: [#13](https://github.com/EngineXV/engineX/issues/13), [#14](https://github.com/EngineXV/engineX/issues/14), [#15](https://github.com/EngineXV/engineX/issues/15). Future multi-tenant SaaS control plane: [#31 Engine Cloud design spec](https://github.com/EngineXV/engineX/issues/31).

## LLM Setup

EngineX requires an LLM for agent nodes.

### Option A — Cloud API Key (Anthropic, OpenAI, etc.)

```bash
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY or OPENAI_API_KEY
./engine run examples/templates/agreement_analysis --tui
./engine setup-credentials examples/templates/agreement_analysis
```

### Option B — Local LLM (Ollama, no API key)

```bash
ollama serve
ollama pull qwen2.5:7b
```

Set default in `~/.engine/configuration.json`:

```json
{
  "llm": {
    "provider": "ollama",
    "model": "qwen2.5:7b"
  }
}
```

Or per run: `./engine run <agent> --model ollama/qwen2.5:7b --tui`

## Project Layout

```
engineX/
├── engine                 # CLI wrapper
├── core/engine/           # Runtime (import: engine)
├── core/frontend/         # Web dashboard (React)
├── tools/                 # MCP tool servers (import: engine_tools)
├── examples/templates/    # 15 reference workflow templates
└── exports/               # Local client agents (gitignored)
```

## Commands

```bash
./engine run <agent> [--tui] [--input '{...}'] [--input-file file.json]
./engine validate <agent>
./engine info <agent>
./engine serve [--host 0.0.0.0] [--port 8787]
./engine setup-credentials <agent>
./engine tui
```

Configuration, sessions, and credentials: `~/.engine/`

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT License](LICENSE)
