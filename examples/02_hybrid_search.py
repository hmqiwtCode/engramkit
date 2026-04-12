"""
Hybrid Search Demo — Compare semantic vs keyword vs hybrid results.

Shows how BM25 keyword search finds exact function names that
semantic search misses, and vice versa.

Usage:
    python examples/02_hybrid_search.py /path/to/repo "your query"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engramkit.storage.vault import VaultManager
from engramkit.search.hybrid import hybrid_search
from engramkit.search.fts import fts_search


def main():
    if len(sys.argv) < 3:
        print("Usage: python examples/02_hybrid_search.py /path/to/repo 'query'")
        sys.exit(1)

    repo_path, query = sys.argv[1], sys.argv[2]
    vault = VaultManager.get_vault(repo_path)

    # 1. BM25 keyword search (SQLite FTS5)
    print(f"=== BM25 Keyword Search: '{query}' ===")
    fts_results = fts_search(vault.conn, query, n_results=5)
    for i, r in enumerate(fts_results, 1):
        print(f"  [{i}] {r['file_path']:40} rank={r['rank']:.4f}")
    if not fts_results:
        print("  (no keyword matches)")

    # 2. Semantic search (ChromaDB vectors)
    print(f"\n=== Semantic Search: '{query}' ===")
    semantic = vault.chroma.search(query, n_results=5)
    for i, r in enumerate(semantic, 1):
        sim = round(1 - r["distance"], 4)
        fpath = r["metadata"].get("file_path", "?")
        print(f"  [{i}] {fpath:40} similarity={sim:.4f}")

    # 3. Hybrid (RRF fusion of both)
    print(f"\n=== Hybrid Search (semantic + BM25): '{query}' ===")
    hybrid = hybrid_search(query, vault, n_results=5)
    for i, r in enumerate(hybrid, 1):
        sources = ", ".join(r.get("sources", []))
        print(f"  [{i}] {r['file_path']:40} score={r['score']:.4f} ({sources})")

    vault.close()


if __name__ == "__main__":
    main()
