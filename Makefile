.PHONY: help lint format check test

help:
	@echo "Engine Makefile targets:"
	@echo "  lint   - ruff check + format (auto-fix)"
	@echo "  format - ruff format only"
	@echo "  check  - ruff check without modifying files"
	@echo "  test   - run framework tests"

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
	cd core && uv run python -m pytest tests/ framework/credentials/tests/ framework/runtime/tests/ -q
