# Contributing to EngramKit

## Development Setup

```bash
# Clone the repository
git clone https://github.com/user/engramkit.git
cd engramkit

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=engramkit

# Run a specific test file
pytest tests/test_vault.py

# Run with verbose output
pytest -v
```

## Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting with a line length of 100.

```bash
# Check for issues
ruff check engramkit/

# Auto-fix what can be fixed
ruff check engramkit/ --fix

# Format code
ruff format engramkit/
```

## Project Layout

- `engramkit/` -- Python package (CLI, MCP server, API, ingest pipeline, search, storage)
- `tests/` -- pytest test suite
- `benchmarks/` -- Benchmark scripts
- `dashboard/` -- Next.js web UI

## Making Changes

1. Create a branch from `main`.
2. Make your changes.
3. Add or update tests as needed.
4. Run `pytest` and `ruff check engramkit/` to verify.
5. Open a pull request with a clear description of what changed and why.

## Dashboard Development

```bash
cd dashboard
npm install
npm run dev
```

The dashboard expects the API server to be running at `http://localhost:8000`:

```bash
python -m engramkit.api.server
```
