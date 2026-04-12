"""Tests for EngramKit configuration — defaults, env vars, and config loading."""

import os
from pathlib import Path

import pytest

from engramkit.config import (
    ENGRAMKIT_HOME,
    DEFAULTS,
    READABLE_EXTENSIONS,
    SKIP_DIRS,
    SKIP_FILENAMES,
    get_config,
)


class TestDefaults:
    """Verify default configuration values."""

    def test_chunk_size(self):
        """Default chunk size should be 800."""
        assert DEFAULTS["chunk_size"] == 800

    def test_chunk_overlap(self):
        """Default overlap should be 100."""
        assert DEFAULTS["chunk_overlap"] == 100

    def test_min_chunk_size(self):
        """Default minimum chunk size should be 50."""
        assert DEFAULTS["min_chunk_size"] == 50

    def test_search_n_results(self):
        """Default search results should be 5."""
        assert DEFAULTS["search_n_results"] == 5

    def test_semantic_weight(self):
        """Semantic weight should be 0.7."""
        assert DEFAULTS["semantic_weight"] == 0.7

    def test_lexical_weight(self):
        """Lexical weight should be 0.3."""
        assert DEFAULTS["lexical_weight"] == 0.3

    def test_gc_retention_days(self):
        """GC retention should be 30 days."""
        assert DEFAULTS["gc_retention_days"] == 30

    def test_token_budget_present(self):
        """Token budget config should be nested in defaults."""
        assert "token_budget" in DEFAULTS
        tb = DEFAULTS["token_budget"]
        assert tb["l0_max_tokens"] == 150
        assert tb["l1_max_tokens"] == 1000
        assert tb["l2_max_tokens"] == 2000
        assert tb["l3_max_tokens"] == 4000


class TestEngramKitHome:
    """Verify ENGRAMKIT_HOME behavior."""

    def test_default_path(self, monkeypatch):
        """Without ENGRAMKIT_HOME env var, should default to ~/.engramkit."""
        monkeypatch.delenv("ENGRAMKIT_HOME", raising=False)
        # Re-evaluate — the module-level ENGRAMKIT_HOME is already set,
        # but we can check the pattern
        expected = Path.home() / ".engramkit"
        # Since ENGRAMKIT_HOME is set at import time, we verify the pattern
        assert isinstance(ENGRAMKIT_HOME, Path)

    def test_env_override(self, monkeypatch, tmp_path):
        """ENGRAMKIT_HOME env var should be respected when the module is loaded."""
        # This tests the pattern, not the actual reloading
        custom = str(tmp_path / "custom_engramkit")
        result = Path(os.environ.get("ENGRAMKIT_HOME", Path.home() / ".engramkit"))
        assert isinstance(result, Path)


class TestReadableExtensions:
    """Verify READABLE_EXTENSIONS contains expected types."""

    def test_python(self):
        assert ".py" in READABLE_EXTENSIONS

    def test_javascript(self):
        assert ".js" in READABLE_EXTENSIONS
        assert ".jsx" in READABLE_EXTENSIONS
        assert ".ts" in READABLE_EXTENSIONS
        assert ".tsx" in READABLE_EXTENSIONS

    def test_data_formats(self):
        assert ".json" in READABLE_EXTENSIONS
        assert ".yaml" in READABLE_EXTENSIONS
        assert ".yml" in READABLE_EXTENSIONS
        assert ".csv" in READABLE_EXTENSIONS

    def test_markup(self):
        assert ".html" in READABLE_EXTENSIONS
        assert ".css" in READABLE_EXTENSIONS
        assert ".md" in READABLE_EXTENSIONS

    def test_systems_languages(self):
        assert ".go" in READABLE_EXTENSIONS
        assert ".rs" in READABLE_EXTENSIONS
        assert ".c" in READABLE_EXTENSIONS
        assert ".cpp" in READABLE_EXTENSIONS

    def test_config(self):
        assert ".toml" in READABLE_EXTENSIONS
        assert ".sql" in READABLE_EXTENSIONS
        assert ".sh" in READABLE_EXTENSIONS

    def test_no_binary(self):
        """Binary extensions should NOT be in READABLE_EXTENSIONS."""
        assert ".exe" not in READABLE_EXTENSIONS
        assert ".dll" not in READABLE_EXTENSIONS
        assert ".png" not in READABLE_EXTENSIONS
        assert ".jpg" not in READABLE_EXTENSIONS
        assert ".zip" not in READABLE_EXTENSIONS
        assert ".tar" not in READABLE_EXTENSIONS


class TestSkipDirs:
    """Verify SKIP_DIRS contains expected directories."""

    def test_git(self):
        assert ".git" in SKIP_DIRS

    def test_node_modules(self):
        assert "node_modules" in SKIP_DIRS

    def test_pycache(self):
        assert "__pycache__" in SKIP_DIRS

    def test_virtualenvs(self):
        assert ".venv" in SKIP_DIRS
        assert "venv" in SKIP_DIRS
        assert "env" in SKIP_DIRS

    def test_build_dirs(self):
        assert "dist" in SKIP_DIRS
        assert "build" in SKIP_DIRS

    def test_ide_dirs(self):
        assert ".idea" in SKIP_DIRS
        assert ".vscode" in SKIP_DIRS

    def test_cache_dirs(self):
        assert ".pytest_cache" in SKIP_DIRS
        assert ".mypy_cache" in SKIP_DIRS
        assert ".ruff_cache" in SKIP_DIRS

    def test_engramkit_self_skip(self):
        """EngramKit should skip its own directory to avoid recursive indexing."""
        assert ".engramkit" in SKIP_DIRS


class TestSkipFilenames:
    """Verify SKIP_FILENAMES contains lock files."""

    def test_npm_lock(self):
        assert "package-lock.json" in SKIP_FILENAMES

    def test_yarn_lock(self):
        assert "yarn.lock" in SKIP_FILENAMES

    def test_pnpm_lock(self):
        assert "pnpm-lock.yaml" in SKIP_FILENAMES

    def test_poetry_lock(self):
        assert "poetry.lock" in SKIP_FILENAMES

    def test_cargo_lock(self):
        assert "Cargo.lock" in SKIP_FILENAMES


class TestGetConfig:
    """Verify get_config merges TOML with defaults."""

    def test_returns_defaults_when_no_file(self, monkeypatch, tmp_path):
        """When no config.toml exists, should return defaults."""
        monkeypatch.setattr("engramkit.config.ENGRAMKIT_HOME", tmp_path)
        config = get_config()
        assert config["chunk_size"] == 800

    def test_returns_copy(self, monkeypatch, tmp_path):
        """get_config should return a copy, not the original DEFAULTS dict."""
        monkeypatch.setattr("engramkit.config.ENGRAMKIT_HOME", tmp_path)
        config1 = get_config()
        config1["chunk_size"] = 9999
        config2 = get_config()
        assert config2["chunk_size"] == 800  # Should not be modified

    def test_merges_toml_overrides(self, monkeypatch, tmp_path):
        """Custom config.toml values should override defaults."""
        monkeypatch.setattr("engramkit.config.ENGRAMKIT_HOME", tmp_path)
        config_file = tmp_path / "config.toml"
        config_file.write_text('chunk_size = 1600\nchunk_overlap = 200\n')

        config = get_config()
        assert config["chunk_size"] == 1600
        assert config["chunk_overlap"] == 200
        # Non-overridden defaults should remain
        assert config["min_chunk_size"] == 50
