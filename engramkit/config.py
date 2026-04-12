"""EngramKit configuration — TOML-based with sensible defaults."""

import os
from pathlib import Path

# Disable CoreML on Apple Silicon — ONNX Runtime tries it, fails, and wastes 10-20s
os.environ.setdefault("ORT_DISABLE_COREML", "1")

# Disable ChromaDB telemetry — prevents any attempt to phone home
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

ENGRAMKIT_HOME = Path(os.environ.get("ENGRAMKIT_HOME", Path.home() / ".engramkit"))

DEFAULTS = {
    "chunk_size": 800,
    "chunk_overlap": 100,
    "min_chunk_size": 50,
    "search_n_results": 5,
    "semantic_weight": 0.7,
    "lexical_weight": 0.3,
    "gc_retention_days": 30,
    "token_budget": {
        "l0_max_tokens": 150,
        "l1_max_tokens": 1000,
        "l2_max_tokens": 2000,
        "l3_max_tokens": 4000,
    },
}

# File types the miner will read
READABLE_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".yaml", ".yml",
    ".html", ".css", ".java", ".go", ".rs", ".rb", ".sh", ".csv", ".sql", ".toml",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".php", ".swift", ".kt", ".scala", ".r",
}

# Directories always skipped
SKIP_DIRS = {
    # Version control
    ".git", ".svn", ".hg",
    # JS/Node dependencies
    "node_modules", "bower_components", ".pnp", "jspm_packages",
    # Python
    "__pycache__", ".venv", "venv", "env", ".eggs", "site-packages",
    # Other language vendors
    "vendor", "Pods", "Carthage",
    # Build output
    "dist", "build", "out", "_build", "target", "bin", "obj",
    ".next", ".nuxt", ".output", ".svelte-kit",
    # Test / coverage
    "coverage", "htmlcov", ".nyc_output", ".pytest_cache", ".tox", ".nox",
    # Cache
    ".cache", ".ruff_cache", ".mypy_cache", ".turbo", ".parcel-cache",
    # IDE
    ".idea", ".vscode", ".vs", ".ipynb_checkpoints",
    # Infra
    ".terraform", ".serverless",
    # EngramKit
    ".engramkit",
}

# Files always skipped
SKIP_FILENAMES = {
    # Lock files
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "Gemfile.lock", "Cargo.lock", "composer.lock", "Pipfile.lock",
    "bun.lockb", "deno.lock",
    # OS files
    ".DS_Store", "Thumbs.db",
}


def get_config() -> dict:
    """Load config from TOML file, falling back to defaults."""
    config_path = ENGRAMKIT_HOME / "config.toml"
    if config_path.exists():
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                return DEFAULTS.copy()
        with open(config_path, "rb") as f:
            user_config = tomllib.load(f)
        merged = DEFAULTS.copy()
        merged.update(user_config)
        return merged
    return DEFAULTS.copy()
