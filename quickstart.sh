#!/bin/bash
# Minimal Engine setup: sync deps, check imports, validate example agent.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "Engine quickstart"
echo "================="

if ! command -v uv >/dev/null 2>&1; then
    echo -e "${RED}uv is required. Install: https://docs.astral.sh/uv/${NC}"
    exit 1
fi

echo -e "${YELLOW}Syncing dependencies...${NC}"
uv sync

echo -e "${YELLOW}Checking core imports...${NC}"
uv run python -c "
import importlib
for mod in ('engine', 'engine_tools', 'litellm'):
    importlib.import_module(mod)
    print(f'  ok: {mod}')
"

if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -z "${OPENAI_API_KEY:-}" ]; then
    echo -e "${YELLOW}Tip: set ANTHROPIC_API_KEY or OPENAI_API_KEY to run agents.${NC}"
fi

echo -e "${YELLOW}Validating example agent...${NC}"
./engine validate examples/templates/contract_review

echo -e "${GREEN}Done. Try: ./engine run examples/templates/contract_review --tui${NC}"
