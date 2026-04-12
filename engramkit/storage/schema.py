"""SQLite schema for EngramKit vaults — metadata spine with FTS5."""

import sqlite3

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS vault_meta (
    key     TEXT PRIMARY KEY,
    value   TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    content_hash    TEXT PRIMARY KEY,
    content         TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    file_hash       TEXT NOT NULL,
    wing            TEXT NOT NULL DEFAULT 'default',
    room            TEXT NOT NULL DEFAULT 'general',
    generation      INTEGER DEFAULT 1,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    last_accessed   TEXT,
    access_count    INTEGER DEFAULT 0,
    importance      REAL DEFAULT 3.0,
    git_commit      TEXT,
    git_branch      TEXT,
    is_stale        INTEGER DEFAULT 0,
    is_secret       INTEGER DEFAULT 0,
    added_by        TEXT DEFAULT 'engramkit'
);

CREATE TABLE IF NOT EXISTS files (
    file_path       TEXT PRIMARY KEY,
    file_hash       TEXT NOT NULL,
    last_mined_at   TEXT NOT NULL,
    last_commit     TEXT,
    chunk_count     INTEGER DEFAULT 0,
    is_deleted      INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS gc_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    action          TEXT NOT NULL,
    content_hash    TEXT,
    file_path       TEXT,
    reason          TEXT,
    performed_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_path);
CREATE INDEX IF NOT EXISTS idx_chunks_wing ON chunks(wing);
CREATE INDEX IF NOT EXISTS idx_chunks_wing_room ON chunks(wing, room);
CREATE INDEX IF NOT EXISTS idx_chunks_gen ON chunks(generation);
CREATE INDEX IF NOT EXISTS idx_chunks_stale ON chunks(is_stale);
CREATE INDEX IF NOT EXISTS idx_files_deleted ON files(is_deleted);
"""

FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    content_hash,
    content,
    file_path,
    wing,
    room,
    content='chunks',
    content_rowid='rowid'
);

-- Triggers to keep FTS in sync with chunks table
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, content_hash, content, file_path, wing, room)
    VALUES (new.rowid, new.content_hash, new.content, new.file_path, new.wing, new.room);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content_hash, content, file_path, wing, room)
    VALUES ('delete', old.rowid, old.content_hash, old.content, old.file_path, old.wing, old.room);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content_hash, content, file_path, wing, room)
    VALUES ('delete', old.rowid, old.content_hash, old.content, old.file_path, old.wing, old.room);
    INSERT INTO chunks_fts(rowid, content_hash, content, file_path, wing, room)
    VALUES (new.rowid, new.content_hash, new.content, new.file_path, new.wing, new.room);
END;
"""


def init_db(db_path: str) -> sqlite3.Connection:
    """Initialize SQLite database with schema and FTS5."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQL)

    # Check if FTS table exists before creating
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='chunks_fts'"
    )
    if cursor.fetchone() is None:
        conn.executescript(FTS_SQL)

    # Store schema version
    conn.execute(
        "INSERT OR REPLACE INTO vault_meta (key, value) VALUES ('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()
    return conn
