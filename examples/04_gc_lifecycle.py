"""
Garbage Collection Demo — Mine, edit, re-mine, and clean up stale chunks.

Shows the full lifecycle: content-addressed IDs detect changes,
generation tracking marks stale chunks, GC removes them.

Usage:
    python examples/04_gc_lifecycle.py
"""

import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engramkit.storage.vault import VaultManager
from engramkit.ingest.pipeline import mine
from engramkit.storage.gc import run_gc


def main():
    # Create a temp project
    project = Path(tempfile.mkdtemp(prefix="engramkit_gc_demo_"))
    (project / "app.py").write_text("def hello():\n    return 'Hello World'\n\ndef goodbye():\n    return 'Goodbye'\n")
    (project / "utils.py").write_text("def add(a, b):\n    return a + b\n")
    print(f"Created project at {project}")

    vault = VaultManager.get_vault(str(project))

    # Mine v1
    print("\n=== Mine v1 ===")
    mine(str(project), vault, wing="demo")
    s = vault.stats()
    print(f"Chunks: {s['total_chunks']}, Stale: {s['stale_chunks']}")

    # Edit file (remove goodbye function)
    print("\n--- Editing app.py (removing goodbye function) ---")
    (project / "app.py").write_text("def hello():\n    return 'Hello World'\n")

    # Mine v2 — detects change, marks old chunks stale
    print("\n=== Mine v2 ===")
    mine(str(project), vault, wing="demo")
    s = vault.stats()
    print(f"Chunks: {s['total_chunks']}, Stale: {s['stale_chunks']}")

    # Delete a file
    print("\n--- Deleting utils.py ---")
    (project / "utils.py").unlink()

    # Mine v3
    print("\n=== Mine v3 ===")
    mine(str(project), vault, wing="demo")
    s = vault.stats()
    print(f"Chunks: {s['total_chunks']}, Stale: {s['stale_chunks']}")

    # GC dry run
    print("\n=== GC Dry Run ===")
    # Backdate stale chunks so GC picks them up
    vault.conn.execute("UPDATE chunks SET updated_at = datetime('now', '-31 days') WHERE is_stale = 1")
    vault.conn.commit()
    run_gc(vault, dry_run=True, retention_days=30)

    # GC execute
    print("\n=== GC Execute ===")
    run_gc(vault, dry_run=False, retention_days=30)
    s = vault.stats()
    print(f"After GC — Chunks: {s['total_chunks']}, Stale: {s['stale_chunks']}")

    vault.close()
    shutil.rmtree(project)
    print("\nDone. Temp project cleaned up.")


if __name__ == "__main__":
    main()
