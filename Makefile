.PHONY: help lint format check test frontend-install frontend-dev frontend-build

help:
	@echo "Engine Makefile targets:"
	@echo "  lint            - ruff check + format (auto-fix)"
	@echo "  format          - ruff format only"
	@echo "  check           - ruff check without modifying files"
	@echo "  test            - run engine tests"
	@echo "  frontend-install - npm install in core/frontend"
	@echo "  frontend-dev    - Vite dev server (proxies API to :8787)"
	@echo "  frontend-build  - production build of dashboard"

lint:
	cd core && uv run ruff check --fix .
	cd tools && uv run ruff check --fix .
	cd core && uv run ruff format .
	cd tools && uv run ruff format .

format:
	cd core && uv run ruff format .
	cd tools && uv run ruff format .

check:
	cd core && uv run ruff check .
	cd tools && uv run ruff check .
	cd core && uv run ruff format --check .
	cd tools && uv run ruff format --check .

test:
	cd core && uv run python -m pytest tests/ -q --cov=engine --cov-report=term-missing
	cd tools && uv run python -m pytest tests/ -q

frontend-install:
	cd core/frontend && npm install --no-fund --no-audit

frontend-dev:
	cd core/frontend && npm run dev

frontend-build:
	cd core/frontend && npm run build
