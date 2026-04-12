"""Tests for garbage collection — mark-and-sweep of stale chunks."""

from datetime import datetime, timedelta

import pytest

from engramkit.storage.vault import Vault
from engramkit.storage.gc import run_gc


@pytest.fixture
def gc_vault(tmp_path):
    """Vault with chunks in various stale/fresh states."""
    vault = Vault(tmp_path / "gc_vault")
    vault.open()

    now = datetime.now()
    old_date = (now - timedelta(days=60)).isoformat()
    recent_date = (now - timedelta(days=5)).isoformat()

    # Fresh chunk — should never be removed
    vault.conn.execute(
        """INSERT INTO chunks
           (content_hash, content, file_path, file_hash, wing, room,
            generation, created_at, updated_at, is_stale)
           VALUES ('fresh1', 'fresh content', 'fresh.py', 'fh1', 'w', 'r', 1, ?, ?, 0)""",
        (now.isoformat(), now.isoformat()),
    )

    # Old stale chunk — eligible for GC (stale + older than retention)
    vault.conn.execute(
        """INSERT INTO chunks
           (content_hash, content, file_path, file_hash, wing, room,
            generation, created_at, updated_at, is_stale)
           VALUES ('stale_old', 'old stale content', 'old.py', 'fh2', 'w', 'r', 1, ?, ?, 1)""",
        (old_date, old_date),
    )

    # Recent stale chunk — NOT eligible (stale but within retention window)
    vault.conn.execute(
        """INSERT INTO chunks
           (content_hash, content, file_path, file_hash, wing, room,
            generation, created_at, updated_at, is_stale)
           VALUES ('stale_recent', 'recent stale content', 'recent.py', 'fh3', 'w', 'r', 1, ?, ?, 1)""",
        (recent_date, recent_date),
    )

    vault.conn.commit()

    # Also put the old stale chunk in ChromaDB so we can verify it's removed
    vault.chroma.batch_upsert(
        ids=["fresh1", "stale_old", "stale_recent"],
        documents=["fresh content", "old stale content", "recent stale content"],
        metadatas=[{"wing": "w"}, {"wing": "w"}, {"wing": "w"}],
    )

    yield vault
    vault.close()


class TestRunGC:
    """Verify garbage collection behavior under various conditions."""

    def test_no_stale_chunks(self, tmp_vault, capsys):
        """GC on a vault with no stale chunks should report nothing to do."""
        # Insert only fresh chunks
        tmp_vault.batch_upsert_chunks([
            {"content_hash": "h1", "content": "fresh", "file_path": "f.py",
             "file_hash": "fh", "wing": "w", "room": "r", "generation": 1},
        ])
        run_gc(tmp_vault, retention_days=0)
        output = capsys.readouterr().out
        assert "No stale chunks" in output

    def test_removes_old_stale_chunks(self, gc_vault):
        """GC should remove chunks that are stale AND older than retention period."""
        run_gc(gc_vault, retention_days=30)

        # Old stale should be gone
        row = gc_vault.conn.execute(
            "SELECT * FROM chunks WHERE content_hash = 'stale_old'"
        ).fetchone()
        assert row is None

        # Fresh should remain
        row = gc_vault.conn.execute(
            "SELECT * FROM chunks WHERE content_hash = 'fresh1'"
        ).fetchone()
        assert row is not None

    def test_respects_retention_period(self, gc_vault):
        """Stale chunks within the retention window should NOT be removed."""
        run_gc(gc_vault, retention_days=30)

        # Recent stale (5 days old) should still be present — within 30-day retention
        row = gc_vault.conn.execute(
            "SELECT * FROM chunks WHERE content_hash = 'stale_recent'"
        ).fetchone()
        assert row is not None

    def test_dry_run_does_not_delete(self, gc_vault, capsys):
        """Dry run should report what would be removed but not delete anything."""
        run_gc(gc_vault, dry_run=True, retention_days=30)
        output = capsys.readouterr().out
        assert "DRY RUN" in output

        # Old stale should still exist
        row = gc_vault.conn.execute(
            "SELECT * FROM chunks WHERE content_hash = 'stale_old'"
        ).fetchone()
        assert row is not None

    def test_gc_log_records_removals(self, gc_vault):
        """Each removed chunk should be recorded in gc_log."""
        run_gc(gc_vault, retention_days=30)

        logs = gc_vault.conn.execute(
            "SELECT * FROM gc_log WHERE action = 'removed'"
        ).fetchall()
        assert len(logs) >= 1
        hashes = {log["content_hash"] for log in logs}
        assert "stale_old" in hashes

    def test_removes_from_chromadb(self, gc_vault):
        """GC should remove stale chunks from ChromaDB as well."""
        initial_count = gc_vault.chroma.count()
        run_gc(gc_vault, retention_days=30)
        # At least one vector removed (stale_old)
        assert gc_vault.chroma.count() < initial_count

    def test_cleans_up_deleted_files(self, gc_vault):
        """Files marked deleted with no remaining chunks should be cleaned up."""
        # Mark the file as deleted
        gc_vault.conn.execute(
            "INSERT INTO files (file_path, file_hash, last_mined_at, is_deleted) "
            "VALUES ('old.py', 'fh2', ?, 1)",
            (datetime.now().isoformat(),),
        )
        gc_vault.conn.commit()

        run_gc(gc_vault, retention_days=30)

        # File record should be cleaned up since all its chunks were removed
        row = gc_vault.conn.execute(
            "SELECT * FROM files WHERE file_path = 'old.py'"
        ).fetchone()
        assert row is None

    def test_gc_with_zero_retention(self, gc_vault):
        """retention_days=0 should remove all stale chunks regardless of age."""
        run_gc(gc_vault, retention_days=0)

        stale = gc_vault.conn.execute(
            "SELECT COUNT(*) as c FROM chunks WHERE is_stale = 1"
        ).fetchone()["c"]
        assert stale == 0
