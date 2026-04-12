"""SQLite FTS5 wrapper — BM25 lexical search."""

import sqlite3


def fts_search(
    conn: sqlite3.Connection,
    query: str,
    n_results: int = 10,
    wing: str = None,
    room: str = None,
) -> list[dict]:
    """
    Full-text search using SQLite FTS5 with BM25 ranking.

    Returns list of {content_hash, content, rank, file_path, wing, room}.
    """
    # Escape FTS5 special characters
    safe_query = _escape_fts_query(query)
    if not safe_query.strip():
        return []

    # Build query with optional filters
    sql = """
        SELECT
            f.content_hash,
            c.content,
            c.file_path,
            c.wing,
            c.room,
            rank
        FROM chunks_fts f
        JOIN chunks c ON c.content_hash = f.content_hash
        WHERE chunks_fts MATCH ?
          AND c.is_stale = 0
          AND c.is_secret = 0
    """
    params = [safe_query]

    if wing:
        sql += " AND c.wing = ?"
        params.append(wing)
    if room:
        sql += " AND c.room = ?"
        params.append(room)

    sql += " ORDER BY rank LIMIT ?"
    params.append(n_results)

    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        # FTS query syntax error — fall back to empty
        return []

    return [
        {
            "content_hash": row["content_hash"],
            "content": row["content"],
            "file_path": row["file_path"],
            "wing": row["wing"],
            "room": row["room"],
            "rank": row["rank"],
        }
        for row in rows
    ]


def _escape_fts_query(query: str) -> str:
    """
    Convert a natural language query to FTS5-safe query.
    Wraps each word in double quotes to treat as literal terms.
    """
    words = query.strip().split()
    if not words:
        return ""
    # Quote each word to avoid FTS5 syntax errors
    return " OR ".join(f'"{w}"' for w in words if w)
