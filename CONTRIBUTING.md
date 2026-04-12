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

## Cutting a Release

Releases are fully automated — push a tag and GitHub Actions publishes to PyPI
and creates a GitHub Release.

**One-time PyPI setup** (maintainers only):

1. Go to https://pypi.org/manage/account/publishing/ and add a *pending publisher*
   with:
   - PyPI project name: `engramkit`
   - Owner: `hmqiwtCode` (GitHub user/org)
   - Repository: `engramkit`
   - Workflow filename: `release.yml`
   - Environment name: `pypi`
2. Create a GitHub environment named `pypi` under repo *Settings → Environments*
   and (optionally) add required reviewers as a protection rule.

**Cutting a release:**

```bash
# 1. Bump the version in pyproject.toml and commit.
#    (The release workflow aborts if the tag and the project version disagree.)
vim pyproject.toml   # e.g. version = "0.2.0"
git add pyproject.toml CHANGELOG.md
git commit -m "chore: release 0.2.0"

# 2. Tag and push.
git tag v0.2.0
git push origin main v0.2.0
```

The `release` workflow will then:

1. Build the sdist and wheel and run `twine check --strict`.
2. Publish to PyPI via OIDC Trusted Publishing (no API tokens, attestations
   generated automatically per PEP 740).
3. Create a GitHub Release with auto-generated notes and attach the dist files.

Pre-release tags (`v0.2.0a1`, `v0.2.0rc1`) also trigger the workflow.
