"""
EngramKit Quick Start — Mine a repo, search it, check status.

Usage:
    python examples/01_quickstart.py /path/to/your/repo
"""

import sys
from pathlib import Path

# Add parent to path if running from examples/
sys.path.insert(0, str(Path(__file__).parent.parent))

from engramkit.storage.vault import VaultManager
from engramkit.ingest.pipeline import mine
from engramkit.search.hybrid import hybrid_search


def main():
    if len(sys.argv) < 2:
        print("Usage: python examples/01_quickstart.py /path/to/repo")
        sys.exit(1)

    repo_path = sys.argv[1]

    # 1. Mine the repo
    print(f"Mining {repo_path}...")
    vault = VaultManager.get_vault(repo_path)
    stats = mine(repo_path, vault)

    # 2. Show status
    s = vault.stats()
    print(f"\nVault: {s['total_chunks']} chunks, {s['total_files']} files, gen {s['generation']}")

    # 3. Search
    query = "how does the main function work"
    print(f"\nSearching: '{query}'")
    results = hybrid_search(query, vault, n_results=3)

    for i, r in enumerate(results, 1):
        sources = ", ".join(r.get("sources", []))
        print(f"  [{i}] {r['file_path']:40} score={r['score']:.4f} ({sources})")
        print(f"      {r['content'][:100]}...")
        print()

    vault.close()
    print("Done.")


if __name__ == "__main__":
    main()
