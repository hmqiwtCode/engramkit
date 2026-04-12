"""Garbage collection — generation-based mark-and-sweep."""

from datetime import datetime, timedelta

from engramkit.storage.vault import Vault


def run_gc(vault: Vault, dry_run: bool = False, retention_days: int = 30):
    """
    Remove stale chunks older than retention_days.

    Stale chunks are marked during mining when:
    - A file's content changes (old chunks marked stale)
    - A file is deleted (all chunks marked stale)
    """
    cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()

    # Find stale chunks eligible for removal
    rows = vault.conn.execute(
        """SELECT content_hash, file_path, updated_at FROM chunks
           WHERE is_stale = 1 AND updated_at < ?""",
        (cutoff,),
    ).fetchall()

    if not rows:
        print(f"\n  No stale chunks older than {retention_days} days.\n")
        return

    print(f"\n{'=' * 55}")
    print(f"  EngramKit GC — {len(rows)} chunks to remove")
    print(f"{'=' * 55}")
    print(f"  Retention: {retention_days} days")
    print(f"  Cutoff:    {cutoff[:10]}")
    if dry_run:
        print("  DRY RUN")
    print(f"{'─' * 55}\n")

    # Group by file for display
    by_file = {}
    for row in rows:
        by_file.setdefault(row["file_path"], []).append(row["content_hash"])

    for fpath, hashes in sorted(by_file.items()):
        print(f"  {fpath}: {len(hashes)} chunks")

    if dry_run:
        print(f"\n  Would remove {len(rows)} chunks. Run without --dry-run to execute.\n")
        return

    # Delete from ChromaDB
    all_hashes = [row["content_hash"] for row in rows]
    vault.chroma.delete(all_hashes)

    # Delete from SQLite
    now = datetime.now().isoformat()
    for row in rows:
        vault.conn.execute(
            "INSERT INTO gc_log (action, content_hash, file_path, reason, performed_at) "
            "VALUES ('removed', ?, ?, 'stale_expired', ?)",
            (row["content_hash"], row["file_path"], now),
        )
        vault.conn.execute("DELETE FROM chunks WHERE content_hash = ?", (row["content_hash"],))

    # Clean up fully deleted files
    vault.conn.execute(
        """DELETE FROM files WHERE is_deleted = 1
           AND file_path NOT IN (SELECT DISTINCT file_path FROM chunks)"""
    )

    vault.conn.commit()

    print(f"\n  Removed {len(rows)} stale chunks.")
    print("  GC log updated.\n")
