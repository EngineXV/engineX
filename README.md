# EngineX

<img src="https://github.com/user-attachments/assets/756e0f11-30c2-46e2-a288-959652101084" alt="EngineX Banner" width="100%">

Open-source goal-driven agent runtime  graphs, event-loop nodes, human-in-the-loop, checkpoints, credentials, CLI, and web dashboard.

## Introduction

EngineX is a robust, open-source framework designed for building and managing goal-driven agents. It provides a comprehensive runtime environment that supports complex workflows through graphs, event-loop nodes, and human-in-the-loop (HITL) interactions. With built-in features for checkpoints, secure credential management, a command-line interface (CLI), and a web dashboard, EngineX empowers developers to create, deploy, and monitor intelligent agents efficiently.

## Key Features

*   **Goal-Driven Agent Runtime**: Orchestrates agents to achieve specific objectives using a flexible and extensible architecture.
*   **Workflow Graphs**: Define and visualize complex agent workflows as interconnected graphs, enabling clear understanding and management of agent interactions.
*   **Event-Loop Nodes**: Facilitates asynchronous and event-driven processing within agent workflows, ensuring responsiveness and efficiency.
*   **Human-in-the-Loop (HITL)**: Integrates human oversight and intervention into automated processes, allowing for validation, decision-making, and error correction.
*   **Checkpoints**: Supports saving and restoring agent states, enabling fault tolerance and the ability to resume operations from a known good point.
*   **Credential Management**: Provides secure handling of API keys and other sensitive information required by agents.
*   **Command-Line Interface (CLI)**: Offers a powerful interface for interacting with the EngineX runtime, including running, validating, and managing agents.
*   **Web Dashboard**: A user-friendly web interface for monitoring agent execution, visualizing workflows, and managing configurations.

## Quick Start

To get started with EngineX, follow these steps:

```bash
git clone https://github.com/EngineXV/engineX.git
cd engineX
uv sync
./engine validate examples/templates/agreement_analysis
./engine run examples/templates/agreement_analysis --tui
```

### Web Dashboard

To access the web dashboard:

```bash
cd core/frontend && npm install && npm run build
cd ../..
./engine serve
```

Open [http://127.0.0.1:8787](http://127.0.0.1:8787) in your browser.

## LLM Setup

EngineX requires an LLM for its agent nodes. Choose one of the following options to set up your LLM:

### Option A — Cloud API Key (Anthropic, OpenAI, etc.)

1.  Copy the environment template and add your API key:

    ```bash
    cp .env.example .env
    # Edit .env — set ANTHROPIC_API_KEY or OPENAI_API_KEY
    ```

2.  Alternatively, export the key in your shell:

    ```bash
    export ANTHROPIC_API_KEY=sk-ant-...
    ```

3.  Run the agent (uses Anthropic by default, or pass a model explicitly):

    ```bash
    ./engine run examples/templates/agreement_analysis --tui
    ./engine run examples/templates/agreement_analysis --model anthropic/claude-sonnet-4-20250514 --tui
    ```

    Guided credential setup is also available:

    ```bash
    ./engine setup-credentials examples/templates/agreement_analysis
    ```

### Option B — Local LLM (Ollama, no API key)

1.  Install and start [Ollama](https://ollama.com):

    ```bash
    ollama serve   # if not already running
    ```

2.  Pull a capable model (recommended for agent tool-calling):

    ```bash
    ollama pull qwen2.5:7b
    # alternatives: llama3.1:8b, qwen2.5:14b
    ```

3.  Set Ollama as the default in `~/.engine/configuration.json`:

    ```json
    {
      "llm": {
        "provider": "ollama",
        "model": "qwen2.5:7b"
      }
    }
    ```

4.  Run the agent:

    ```bash
    ./engine run examples/templates/agreement_analysis --tui
    ```

    Or pass the model for a single run without changing config:

    ```bash
    ./engine run examples/templates/agreement_analysis --model ollama/qwen2.5:7b --tui
    ```

    Other local prefixes supported: `ollama_chat/`, `vllm/`, `lm_studio/`, `llamacpp/`.

## Project Layout

The EngineX project has the following directory structure:

```
engine/
├── engine              # CLI wrapper script
├── core/engine/        # Runtime package (import: engine)
├── tools/              # MCP data tools (import: engine_tools)
└── examples/templates/agreement_analysis/
```

## Commands

Here is a list of commonly used EngineX commands:

```bash
./engine run <agent> [--tui] [--input '{...}']
./engine validate <agent>
./engine info <agent>
./engine tui
./engine shell <agent>
./engine setup-credentials <agent>
```

Configuration and credentials are managed in `~/.engine/`.

## Documentation

| Doc | Audience |
|-----|----------|
| [ENGINEX_COMPLETE_GUIDE.md](docs/ENGINEX_COMPLETE_GUIDE.md) | Product overview, diagrams, code map |
| [GOALS.md](docs/GOALS.md) | Goal vs node criteria, four feedback mechanisms |
| [CLIENT_DEPLOYMENT_GUIDE.md](docs/CLIENT_DEPLOYMENT_GUIDE.md) | Client cloud install — headless vs dashboard |
| [MULTI_TENANT.md](docs/MULTI_TENANT.md) | Multi-tenant SaaS design (Phase 2 — not in OSS) |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Engineering architecture summary |
| [docs/TICKET_STATUS.md](docs/TICKET_STATUS.md) | GitHub / internal ticket audit (post PR #9–#12) |

```bash
./engine serve   # Dashboard at http://127.0.0.1:8787
```

## Architecture Overview

EngineX is built around a modular and scalable architecture that leverages graphs for defining agent workflows, event-loop nodes for efficient processing, and human-in-the-loop mechanisms for robust control. It supports features like checkpoints for state management and secure credential handling, all accessible via a powerful CLI and a comprehensive web dashboard. The system is designed to facilitate the development and deployment of production-ready agentic workflows.

## Contributing

We welcome contributions to EngineX! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute.

## License

EngineX is open-source software released under the [MIT License](LICENSE).
