# Contributing to Engine

Thanks for your interest in Engine. This project is open source and welcomes contributions.

## Getting started

```bash
git clone https://github.com/EngineXV/engineX.git
cd engineX
uv sync
make check
make test
```

## Development workflow

1. Fork the repo and create a branch from `main`.
2. Make focused changes with tests when behavior changes.
3. Run `make lint` and `make check` before opening a PR.
4. Open a pull request with a clear description and test plan.

## Agent examples

New example agents live under `examples/templates/`. Validate before submitting:

```bash
./engine validate examples/templates/your_agent
```

## Code style

- Python 3.11+, formatted and linted with ruff (`core/pyproject.toml`)
- Type hints on public functions
- Keep diffs focused; avoid unrelated refactors

## Security

Do not commit secrets, API keys, or `.env` files. Use `.env.example` for documentation only.

Report security issues privately to the maintainers instead of opening a public issue.

## Questions

Open a GitHub Discussion or issue if you are unsure where a change belongs.
