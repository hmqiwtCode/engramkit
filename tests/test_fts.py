"""Tests for SQLite FTS5 full-text search (BM25 lexical search)."""

import pytest

from engramkit.storage.vault import Vault
from engramkit.search.fts import fts_search, _escape_fts_query


@pytest.fixture
def fts_vault(tmp_path):
    """Vault with chunks for FTS testing."""
    vault = Vault(tmp_path / "fts_vault")
    vault.open()
    chunks = [
        {
            "content_hash": "fts1",
            "content": "def calculate_total(items, discount):\n    validate(items)\n    return sum(items) * (1 - discount)",
            "file_path": "billing.py",
            "file_hash": "f1",
            "wing": "api",
            "room": "billing",
            "generation": 1,
        },
        {
            "content_hash": "fts2",
            "content": "PostgreSQL database connection pool with asyncpg library",
            "file_path": "db.py",
            "file_hash": "f2",
            "wing": "api",
            "room": "database",
            "generation": 1,
        },
        {
            "content_hash": "fts3",
            "content": "async def handle_webhook(request):\n    validate_signature(request)",
            "file_path": "webhook.py",
            "file_hash": "f3",
            "wing": "backend",
            "room": "webhooks",
            "generation": 1,
        },
        {
            "content_hash": "fts_secret",
            "content": "SECRET_KEY=super_secret_password_12345678",
            "file_path": ".env",
            "file_hash": "f4",
            "wing": "api",
            "room": "general",
            "generation": 1,
            "is_secret": 1,
        },
    ]
    vault.batch_upsert_chunks(chunks)
    yield vault
    vault.close()


class TestFTSSearch:
    """Verify FTS5 search returns correct, filtered, and ranked results."""

    def test_exact_keyword_match(self, fts_vault):
        """Searching for an exact function name should find the right chunk."""
        results = fts_search(fts_vault.conn, "calculate_total")
        assert len(results) >= 1
        assert results[0]["content_hash"] == "fts1"

    def test_returns_empty_for_no_match(self, fts_vault):
        """A query with no matching words should return empty list."""
        results = fts_search(fts_vault.conn, "xyznonexistent")
        assert results == []

    def test_wing_filter(self, fts_vault):
        """Wing filter should restrict results."""
        results = fts_search(fts_vault.conn, "validate", wing="backend")
        for r in results:
            assert r["wing"] == "backend"

    def test_wing_filter_excludes_other_wings(self, fts_vault):
        """Filtering by wrong wing should return empty."""
        results = fts_search(fts_vault.conn, "PostgreSQL", wing="nonexistent")
        assert results == []

    def test_room_filter(self, fts_vault):
        """Room filter should restrict results."""
        results = fts_search(fts_vault.conn, "connection", room="database")
        assert len(results) >= 1
        for r in results:
            assert r["room"] == "database"

    def test_combined_wing_and_room_filter(self, fts_vault):
        """Both wing and room filters should work together."""
        results = fts_search(fts_vault.conn, "calculate_total", wing="api", room="billing")
        assert len(results) >= 1
        for r in results:
            assert r["wing"] == "api"
            assert r["room"] == "billing"

    def test_secrets_excluded(self, fts_vault):
        """Secret chunks should not appear in FTS results."""
        results = fts_search(fts_vault.conn, "SECRET_KEY")
        hashes = [r["content_hash"] for r in results]
        assert "fts_secret" not in hashes

    def test_result_structure(self, fts_vault):
        """Each result should have content_hash, content, file_path, wing, room, rank."""
        results = fts_search(fts_vault.conn, "database")
        assert len(results) >= 1
        r = results[0]
        assert "content_hash" in r
        assert "content" in r
        assert "file_path" in r
        assert "wing" in r
        assert "room" in r
        assert "rank" in r

    def test_rank_ordering(self, fts_vault):
        """Results should be ordered by BM25 rank (lower is better)."""
        results = fts_search(fts_vault.conn, "validate", n_results=10)
        if len(results) >= 2:
            # FTS5 rank: more negative = more relevant
            assert results[0]["rank"] <= results[1]["rank"]

    def test_n_results_limit(self, fts_vault):
        """Should return at most n_results items."""
        results = fts_search(fts_vault.conn, "validate", n_results=1)
        assert len(results) <= 1

    def test_stale_chunks_excluded(self, fts_vault):
        """Stale chunks should not appear in FTS results."""
        # Mark a chunk as stale
        fts_vault.mark_stale({"fts1"})
        results = fts_search(fts_vault.conn, "calculate_total")
        hashes = [r["content_hash"] for r in results]
        assert "fts1" not in hashes


class TestEscapeFTSQuery:
    """Verify FTS query escaping handles special characters safely."""

    def test_simple_words(self):
        """Simple words should be quoted."""
        result = _escape_fts_query("hello world")
        assert '"hello"' in result
        assert '"world"' in result

    def test_empty_query(self):
        """Empty string should return empty."""
        assert _escape_fts_query("") == ""
        assert _escape_fts_query("   ") == ""

    def test_special_characters(self):
        """Words with special FTS5 characters should be safely wrapped."""
        result = _escape_fts_query("AND OR NOT")
        # Each word should be quoted to prevent FTS5 operator interpretation
        assert '"AND"' in result
        assert '"OR"' in result
        assert '"NOT"' in result

    def test_single_word(self):
        """Single word should be quoted."""
        result = _escape_fts_query("hello")
        assert result == '"hello"'

    def test_or_joined(self):
        """Multiple words should be joined with OR."""
        result = _escape_fts_query("alpha beta")
        assert "OR" in result
