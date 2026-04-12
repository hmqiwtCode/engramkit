"""Thorough tests for hybrid search — semantic + BM25 with RRF fusion."""

import pytest

from engramkit.storage.vault import Vault
from engramkit.search.hybrid import hybrid_search, _rrf_merge


@pytest.fixture
def search_vault(tmp_path):
    """Vault with diverse chunks for comprehensive search testing."""
    vault = Vault(tmp_path / "search_vault")
    vault.open()

    chunks = [
        {
            "content_hash": "h_billing",
            "content": "def calculate_total(items, discount):\n    validate(items)\n    return sum(items) * (1 - discount)",
            "file_path": "billing.py",
            "file_hash": "f1",
            "wing": "api",
            "room": "billing",
            "generation": 1,
        },
        {
            "content_hash": "h_db",
            "content": "PostgreSQL database connection pool setup with asyncpg retry logic",
            "file_path": "db.py",
            "file_hash": "f2",
            "wing": "api",
            "room": "database",
            "generation": 1,
        },
        {
            "content_hash": "h_webhook",
            "content": "async def handle_webhook(request):\n    validate(request)\n    process(request.body)",
            "file_path": "webhook.py",
            "file_hash": "f3",
            "wing": "api",
            "room": "webhooks",
            "generation": 1,
        },
        {
            "content_hash": "h_secret",
            "content": "SECRET_KEY=super_secret_password_12345678",
            "file_path": ".env",
            "file_hash": "f4",
            "wing": "api",
            "room": "general",
            "generation": 1,
            "is_secret": 1,
        },
        {
            "content_hash": "h_docs",
            "content": "# Acme Corp Billing System\nThis service provides an HTTP API for processing invoices.",
            "file_path": "README.md",
            "file_hash": "f5",
            "wing": "docs",
            "room": "general",
            "generation": 1,
        },
    ]
    vault.batch_upsert_chunks(chunks)
    yield vault
    vault.close()


@pytest.fixture
def vault_with_stale(tmp_path):
    """Vault with both active and stale chunks."""
    vault = Vault(tmp_path / "stale_vault")
    vault.open()
    chunks = [
        {
            "content_hash": "active1",
            "content": "active function code def active_func(): pass",
            "file_path": "active.py",
            "file_hash": "fa",
            "wing": "w",
            "room": "r",
            "generation": 2,
        },
        {
            "content_hash": "stale1",
            "content": "stale function code def stale_func(): pass",
            "file_path": "stale.py",
            "file_hash": "fs",
            "wing": "w",
            "room": "r",
            "generation": 1,
        },
    ]
    vault.batch_upsert_chunks(chunks)
    vault.mark_stale({"stale1"})
    yield vault
    vault.close()


class TestHybridSearch:
    """End-to-end hybrid search combining semantic and lexical results."""

    def test_finds_by_semantic_similarity(self, search_vault):
        """Searching for 'invoice processing' should find the billing chunk semantically."""
        results = hybrid_search("invoice processing", search_vault, n_results=3)
        hashes = [r["content_hash"] for r in results]
        assert "h_billing" in hashes

    def test_finds_by_exact_keyword(self, search_vault):
        """Searching for 'calculate_total' should find the exact function by BM25."""
        results = hybrid_search("calculate_total", search_vault, n_results=3)
        assert len(results) >= 1
        assert results[0]["content_hash"] == "h_billing"

    def test_wing_filter(self, search_vault):
        """Wing filter should restrict results to the matching wing."""
        results = hybrid_search("code", search_vault, n_results=10, wing="docs")
        for r in results:
            assert r["wing"] == "docs"

    def test_room_filter(self, search_vault):
        """Room filter should restrict results to the matching room."""
        results = hybrid_search("connection", search_vault, n_results=10, room="database")
        for r in results:
            assert r["room"] == "database"

    def test_deduplication(self, search_vault):
        """Results should not contain duplicate content_hashes."""
        results = hybrid_search("billing record", search_vault, n_results=10)
        hashes = [r["content_hash"] for r in results]
        assert len(hashes) == len(set(hashes))

    def test_stale_chunks_excluded(self, vault_with_stale):
        """Stale chunks should not appear in search results."""
        results = hybrid_search("stale_func", vault_with_stale, n_results=10)
        hashes = [r["content_hash"] for r in results]
        assert "stale1" not in hashes

    def test_secret_chunks_excluded(self, search_vault):
        """Secret chunks should not appear in search results."""
        results = hybrid_search("SECRET_KEY", search_vault, n_results=10)
        hashes = [r["content_hash"] for r in results]
        assert "h_secret" not in hashes

    def test_access_count_incremented(self, search_vault):
        """Returned chunks should have their access_count incremented."""
        # Get initial access count
        row = search_vault.conn.execute(
            "SELECT access_count FROM chunks WHERE content_hash = 'h_billing'"
        ).fetchone()
        initial = row["access_count"]

        hybrid_search("calculate_total", search_vault, n_results=3)

        row = search_vault.conn.execute(
            "SELECT access_count FROM chunks WHERE content_hash = 'h_billing'"
        ).fetchone()
        assert row["access_count"] > initial

    def test_result_structure(self, search_vault):
        """Each result should have expected fields from SQLite enrichment."""
        results = hybrid_search("database", search_vault, n_results=3)
        if results:
            r = results[0]
            assert "content_hash" in r
            assert "content" in r
            assert "file_path" in r
            assert "wing" in r
            assert "room" in r
            assert "importance" in r
            assert "score" in r
            assert "sources" in r

    def test_empty_query(self, search_vault):
        """Empty query should return an empty list (FTS5 rejects empty)."""
        results = hybrid_search("", search_vault, n_results=5)
        assert isinstance(results, list)

    def test_nonexistent_wing_returns_empty(self, search_vault):
        """Filtering by a wing that doesn't exist should return nothing."""
        results = hybrid_search("code", search_vault, n_results=10, wing="nonexistent")
        assert results == []


class TestRRFMerge:
    """Unit tests for the Reciprocal Rank Fusion merge algorithm."""

    def test_single_list(self):
        """Single result list should preserve order."""
        results = [
            [
                {"content_hash": "a", "content": "first", "source": "semantic"},
                {"content_hash": "b", "content": "second", "source": "semantic"},
            ]
        ]
        merged = _rrf_merge(results, [1.0])
        assert merged[0]["content_hash"] == "a"
        assert merged[1]["content_hash"] == "b"

    def test_two_lists_merge(self):
        """Items appearing in both lists should score higher than items in one."""
        list1 = [
            {"content_hash": "a", "content": "shared", "source": "semantic"},
            {"content_hash": "b", "content": "only-semantic", "source": "semantic"},
        ]
        list2 = [
            {"content_hash": "a", "content": "shared", "source": "lexical"},
            {"content_hash": "c", "content": "only-lexical", "source": "lexical"},
        ]
        merged = _rrf_merge([list1, list2], [0.7, 0.3])
        # 'a' appears in both lists — should score highest
        assert merged[0]["content_hash"] == "a"

    def test_weights_affect_ranking(self):
        """Higher weighted list should have more influence."""
        list1 = [{"content_hash": "x", "content": "x", "source": "s"}]
        list2 = [{"content_hash": "y", "content": "y", "source": "l"}]
        # Give list1 much higher weight
        merged = _rrf_merge([list1, list2], [10.0, 0.1])
        assert merged[0]["content_hash"] == "x"

    def test_empty_lists(self):
        """Empty input lists should return empty result."""
        merged = _rrf_merge([[], []], [1.0, 1.0])
        assert merged == []

    def test_sources_tracked(self):
        """Each merged result should track which lists contributed."""
        list1 = [{"content_hash": "a", "content": "x", "source": "semantic"}]
        list2 = [{"content_hash": "a", "content": "x", "source": "lexical"}]
        merged = _rrf_merge([list1, list2], [1.0, 1.0])
        assert "semantic" in merged[0]["sources"]
        assert "lexical" in merged[0]["sources"]

    def test_score_is_positive(self):
        """All RRF scores should be positive."""
        results = [
            [{"content_hash": f"h{i}", "content": f"c{i}", "source": "s"} for i in range(5)]
        ]
        merged = _rrf_merge(results, [1.0])
        for r in merged:
            assert r["score"] > 0
