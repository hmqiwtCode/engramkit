"""Tests for ChromaDB vector backend — batch upsert, search, delete, count."""

import pytest

from engramkit.storage.chromadb_backend import ChromaBackend


@pytest.fixture
def chroma(tmp_path):
    """Fresh ChromaDB backend in a temp directory."""
    return ChromaBackend(str(tmp_path / "vectors"))


class TestBatchUpsert:
    """Verify batch_upsert handles normal, empty, and duplicate inputs."""

    def test_basic_upsert(self, chroma):
        """Upserting documents should make them searchable."""
        chroma.batch_upsert(
            ids=["a", "b"],
            documents=["hello world", "goodbye world"],
            metadatas=[{"wing": "w1"}, {"wing": "w2"}],
        )
        assert chroma.count() == 2

    def test_empty_list(self, chroma):
        """Upserting empty lists should be a no-op."""
        chroma.batch_upsert(ids=[], documents=[], metadatas=[])
        assert chroma.count() == 0

    def test_deduplication_within_batch(self, chroma):
        """Duplicate IDs within a single batch should be deduplicated."""
        chroma.batch_upsert(
            ids=["dup", "dup", "dup"],
            documents=["first", "second", "third"],
            metadatas=[{"v": "1"}, {"v": "2"}, {"v": "3"}],
        )
        # Only the first occurrence should be stored
        assert chroma.count() == 1

    def test_upsert_overwrites_existing(self, chroma):
        """Upserting an existing ID should overwrite the document."""
        chroma.batch_upsert(
            ids=["x"],
            documents=["original content"],
            metadatas=[{"wing": "w"}],
        )
        chroma.batch_upsert(
            ids=["x"],
            documents=["updated content"],
            metadatas=[{"wing": "w"}],
        )
        assert chroma.count() == 1
        results = chroma.search("updated content", n_results=1)
        assert len(results) == 1
        assert "updated" in results[0]["content"]


class TestSearch:
    """Verify search returns correct structure and respects filters."""

    @pytest.fixture(autouse=True)
    def _seed(self, chroma):
        """Seed 3 documents for search tests."""
        chroma.batch_upsert(
            ids=["s1", "s2", "s3"],
            documents=[
                "Python function for processing billing records",
                "PostgreSQL database connection pooling",
                "JavaScript React component for dashboard",
            ],
            metadatas=[
                {"wing": "api", "room": "billing", "file_path": "billing.py"},
                {"wing": "api", "room": "db", "file_path": "db.py"},
                {"wing": "frontend", "room": "ui", "file_path": "App.jsx"},
            ],
        )

    def test_returns_correct_structure(self, chroma):
        """Each result should have content_hash, content, distance, metadata."""
        results = chroma.search("invoice", n_results=1)
        assert len(results) >= 1
        r = results[0]
        assert "content_hash" in r
        assert "content" in r
        assert "distance" in r
        assert "metadata" in r

    def test_search_relevance(self, chroma):
        """Searching for 'invoice' should rank the billing document highest."""
        results = chroma.search("billing records", n_results=3)
        assert results[0]["content_hash"] == "s1"

    def test_search_with_where_filter(self, chroma):
        """Where filter should restrict results to matching metadata."""
        results = chroma.search("code", n_results=10, where={"wing": "frontend"})
        for r in results:
            assert r["metadata"]["wing"] == "frontend"

    def test_search_no_results(self, chroma):
        """Querying for nonexistent content should return empty list."""
        results = chroma.search("xyznonexistent", n_results=5, where={"wing": "nonexistent_wing"})
        assert results == []

    def test_search_n_results_limit(self, chroma):
        """Should return at most n_results items."""
        results = chroma.search("connection", n_results=1)
        assert len(results) <= 1


class TestDelete:
    """Verify delete removes vectors and count reflects changes."""

    def test_delete_reduces_count(self, chroma):
        """Deleting a document should reduce the count."""
        chroma.batch_upsert(
            ids=["d1", "d2", "d3"],
            documents=["aaa", "bbb", "ccc"],
            metadatas=[{"wing": "w"}, {"wing": "w"}, {"wing": "w"}],
        )
        assert chroma.count() == 3
        chroma.delete(["d1"])
        assert chroma.count() == 2

    def test_delete_multiple(self, chroma):
        """Deleting multiple IDs at once should work."""
        chroma.batch_upsert(
            ids=["m1", "m2", "m3"],
            documents=["aaa", "bbb", "ccc"],
            metadatas=[{"wing": "w"}, {"wing": "w"}, {"wing": "w"}],
        )
        chroma.delete(["m1", "m2", "m3"])
        assert chroma.count() == 0

    def test_delete_empty_list(self, chroma):
        """Deleting an empty list should be a no-op."""
        chroma.batch_upsert(ids=["e1"], documents=["data"], metadatas=[{"wing": "w"}])
        chroma.delete([])
        assert chroma.count() == 1

    def test_delete_nonexistent_id(self, chroma):
        """Deleting a nonexistent ID should not error."""
        chroma.delete(["nonexistent_id"])  # Should not raise

    def test_deleted_not_searchable(self, chroma):
        """Deleted documents should not appear in search results."""
        chroma.batch_upsert(
            ids=["gone"],
            documents=["unique_content_for_deletion_test"],
            metadatas=[{"wing": "w"}],
        )
        chroma.delete(["gone"])
        results = chroma.search("unique_content_for_deletion_test", n_results=5)
        assert all(r["content_hash"] != "gone" for r in results)


class TestCount:
    """Verify count reflects the current state."""

    def test_empty_collection(self, chroma):
        """New collection should have count 0."""
        assert chroma.count() == 0

    def test_count_after_upsert(self, chroma):
        """Count should equal the number of unique documents."""
        chroma.batch_upsert(
            ids=["c1", "c2"],
            documents=["aa", "bb"],
            metadatas=[{"wing": "w"}, {"wing": "w"}],
        )
        assert chroma.count() == 2
