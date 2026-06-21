# Engine

Open-source goal-driven agent runtime — graphs, event-loop nodes, human-in-the-loop, checkpoints, credentials, CLI, and web dashboard.

## Quick start

```bash
git clone https://github.com/EngineXV/engineX.git
cd engineX
uv sync
./engine validate examples/templates/agreement_analysis
./engine run examples/templates/agreement_analysis --tui
```

### Web dashboard

```bash
cd core/frontend && npm install && npm run build
cd ../..
./engine serve
```

Open http://127.0.0.1:8787

## LLM setup

Engine needs an LLM for agent nodes. Pick **one** of the options below.

### Option A — Cloud API key (Anthropic, OpenAI, etc.)

1. Copy the env template and add your key:

   ```bash
   cp .env.example .env
   # Edit .env — set ANTHROPIC_API_KEY or OPENAI_API_KEY
   ```

2. Or export the key in your shell:

   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   ```

3. Run the agent (uses Anthropic by default, or pass a model explicitly):

   ```bash
   ./engine run examples/templates/agreement_analysis --tui
   ./engine run examples/templates/agreement_analysis --model anthropic/claude-sonnet-4-20250514 --tui
   ```

   Guided credential setup is also available:

   ```bash
   ./engine setup-credentials examples/templates/agreement_analysis
   ```

### Option B — Local LLM (Ollama, no API key)

1. Install and start [Ollama](https://ollama.com):

   ```bash
   ollama serve   # if not already running
   ```

2. Pull a capable model (recommended for agent tool-calling):

   ```bash
   ollama pull qwen2.5:7b
   # alternatives: llama3.1:8b, qwen2.5:14b
   ```

3. Set Ollama as the default in `~/.engine/configuration.json`:

   ```json
   {
     "llm": {
       "provider": "ollama",
       "model": "qwen2.5:7b"
     }
   }
   ```

4. Run the agent:

   ```bash
   ./engine run examples/templates/agreement_analysis --tui
   ```

   Or pass the model for a single run without changing config:

   ```bash
   ./engine run examples/templates/agreement_analysis --model ollama/qwen2.5:7b --tui
   ```

   Other local prefixes supported: `ollama_chat/`, `vllm/`, `lm_studio/`, `llamacpp/`.

## Layout

```
engine/
├── engine              # CLI wrapper script
├── core/engine/        # Runtime package (import: engine)
├── tools/              # MCP data tools (import: engine_tools)
└── examples/templates/agreement_analysis/
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

Architecture overview: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
