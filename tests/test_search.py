"""Tests for hybrid search."""

import pytest

from engramkit.storage.vault import Vault
from engramkit.search.fts import fts_search


@pytest.fixture
def vault_with_data(tmp_path):
    vault = Vault(tmp_path / "search_vault")
    vault.open()

    chunks = [
        {"content_hash": "h1", "content": "def calculate_total(items, discount): pass",
         "file_path": "billing.py", "file_hash": "f1", "wing": "api", "room": "billing", "generation": 1},
        {"content_hash": "h2", "content": "PostgreSQL database connection pool setup",
         "file_path": "db.py", "file_hash": "f2", "wing": "api", "room": "database", "generation": 1},
        {"content_hash": "h3", "content": "async def handle_webhook(request): validate(request)",
         "file_path": "webhook.py", "file_hash": "f3", "wing": "api", "room": "webhooks", "generation": 1},
        {"content_hash": "h4", "content": "SECRET_KEY=super_secret_password_12345678",
         "file_path": ".env", "file_hash": "f4", "wing": "api", "room": "general",
         "generation": 1, "is_secret": 1},
    ]
    vault.batch_upsert_chunks(chunks)
    yield vault
    vault.close()


class TestFTSSearch:
    def test_keyword_match(self, vault_with_data):
        results = fts_search(vault_with_data.conn, "calculate_total")
        assert len(results) >= 1
        assert results[0]["content_hash"] == "h1"

    def test_no_match(self, vault_with_data):
        results = fts_search(vault_with_data.conn, "xyznonexistent")
        assert len(results) == 0

    def test_secrets_excluded(self, vault_with_data):
        results = fts_search(vault_with_data.conn, "SECRET_KEY")
        # Secret chunks should be excluded by is_secret=1 filter
        for r in results:
            assert r["content_hash"] != "h4"

    def test_wing_filter(self, vault_with_data):
        results = fts_search(vault_with_data.conn, "PostgreSQL", wing="api")
        assert len(results) >= 1
        results_wrong = fts_search(vault_with_data.conn, "PostgreSQL", wing="nonexistent")
        assert len(results_wrong) == 0


class TestHybridSearch:
    def test_returns_results(self, vault_with_data):
        from engramkit.search.hybrid import hybrid_search
        results = hybrid_search("process invoice", vault_with_data, n_results=3)
        assert len(results) >= 1

    def test_deduplication(self, vault_with_data):
        from engramkit.search.hybrid import hybrid_search
        results = hybrid_search("database connection", vault_with_data, n_results=5)
        hashes = [r["content_hash"] for r in results]
        assert len(hashes) == len(set(hashes))  # No duplicates
