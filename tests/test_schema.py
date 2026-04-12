"""Tests for SQLite schema initialization, FTS5, and triggers."""

import sqlite3


from engramkit.storage.schema import init_db, SCHEMA_VERSION


class TestInitDb:
    """Verify init_db creates all expected tables, indexes, and triggers."""

    def test_creates_all_tables(self, tmp_path):
        """init_db should create chunks, files, gc_log, vault_meta, and chunks_fts."""
        conn = init_db(str(tmp_path / "test.sqlite3"))
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn.close()
        assert "chunks" in tables
        assert "files" in tables
        assert "gc_log" in tables
        assert "vault_meta" in tables
        assert "chunks_fts" in tables

    def test_fts5_virtual_table_exists(self, tmp_path):
        """chunks_fts should be a virtual FTS5 table."""
        conn = init_db(str(tmp_path / "test.sqlite3"))
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name='chunks_fts'"
        ).fetchone()
        conn.close()
        assert row is not None
        sql = row[0] if isinstance(row, tuple) else row["sql"]
        assert "fts5" in sql.lower()

    def test_schema_version_stored(self, tmp_path):
        """vault_meta should contain the schema version."""
        conn = init_db(str(tmp_path / "test.sqlite3"))
        row = conn.execute(
            "SELECT value FROM vault_meta WHERE key = 'schema_version'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["value"] == str(SCHEMA_VERSION)

    def test_idempotent(self, tmp_path):
        """Calling init_db twice on the same file should not error."""
        db_path = str(tmp_path / "test.sqlite3")
        conn1 = init_db(db_path)
        conn1.close()
        conn2 = init_db(db_path)
        tables = {
            row[0]
            for row in conn2.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn2.close()
        assert "chunks" in tables

    def test_wal_mode_enabled(self, tmp_path):
        """Database should be opened in WAL journal mode."""
        conn = init_db(str(tmp_path / "test.sqlite3"))
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert mode == "wal"

    def test_row_factory_is_row(self, tmp_path):
        """Rows should be accessible by column name."""
        conn = init_db(str(tmp_path / "test.sqlite3"))
        assert conn.row_factory == sqlite3.Row
        conn.close()


class TestFTSTriggers:
    """Verify that insert/update/delete triggers keep chunks_fts in sync."""

    def _insert_chunk(self, conn, content_hash, content, file_path="t.py"):
        """Helper to insert a chunk directly into the chunks table."""
        from datetime import datetime
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO chunks
               (content_hash, content, file_path, file_hash, wing, room,
                generation, created_at, updated_at)
               VALUES (?, ?, ?, 'fh', 'w', 'r', 1, ?, ?)""",
            (content_hash, content, file_path, now, now),
        )
        conn.commit()

    def test_insert_syncs_to_fts(self, db_conn):
        """Inserting into chunks should auto-populate chunks_fts via trigger."""
        self._insert_chunk(db_conn, "abc", "def calculate_total(): pass")
        # FTS5 tokenizes underscores, so search for individual words
        results = db_conn.execute(
            "SELECT * FROM chunks_fts WHERE chunks_fts MATCH '\"calculate\"'"
        ).fetchall()
        assert len(results) == 1
        assert results[0]["content_hash"] == "abc"

    def test_delete_syncs_to_fts(self, db_conn):
        """Deleting from chunks should remove from chunks_fts via trigger."""
        self._insert_chunk(db_conn, "del1", "unique_delete_keyword_xyz")
        # Verify present
        assert len(db_conn.execute(
            "SELECT * FROM chunks_fts WHERE chunks_fts MATCH '\"unique_delete_keyword_xyz\"'"
        ).fetchall()) == 1
        # Delete
        db_conn.execute("DELETE FROM chunks WHERE content_hash = 'del1'")
        db_conn.commit()
        # Verify removed
        results = db_conn.execute(
            "SELECT * FROM chunks_fts WHERE chunks_fts MATCH '\"unique_delete_keyword_xyz\"'"
        ).fetchall()
        assert len(results) == 0

    def test_update_syncs_to_fts(self, db_conn):
        """Updating chunk content should update chunks_fts via trigger."""
        self._insert_chunk(db_conn, "upd1", "old_content_before_update")
        # Update content
        db_conn.execute(
            "UPDATE chunks SET content = 'new_content_after_update' WHERE content_hash = 'upd1'"
        )
        db_conn.commit()
        # Old content gone
        old = db_conn.execute(
            "SELECT * FROM chunks_fts WHERE chunks_fts MATCH '\"old_content_before_update\"'"
        ).fetchall()
        assert len(old) == 0
        # New content present
        new = db_conn.execute(
            "SELECT * FROM chunks_fts WHERE chunks_fts MATCH '\"new_content_after_update\"'"
        ).fetchall()
        assert len(new) == 1

    def test_multiple_chunks_searchable(self, db_conn):
        """FTS should index multiple chunks independently."""
        self._insert_chunk(db_conn, "m1", "alpha bravo charlie")
        self._insert_chunk(db_conn, "m2", "delta echo foxtrot")
        self._insert_chunk(db_conn, "m3", "golf hotel india")

        r1 = db_conn.execute(
            "SELECT * FROM chunks_fts WHERE chunks_fts MATCH '\"bravo\"'"
        ).fetchall()
        assert len(r1) == 1

        r2 = db_conn.execute(
            "SELECT * FROM chunks_fts WHERE chunks_fts MATCH '\"echo\"'"
        ).fetchall()
        assert len(r2) == 1


class TestIndexes:
    """Verify expected indexes exist."""

    def test_indexes_created(self, db_conn):
        indexes = {
            row[0]
            for row in db_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        assert "idx_chunks_file" in indexes
        assert "idx_chunks_wing" in indexes
        assert "idx_chunks_wing_room" in indexes
        assert "idx_chunks_gen" in indexes
        assert "idx_chunks_stale" in indexes
        assert "idx_files_deleted" in indexes
