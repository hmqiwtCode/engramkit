"""
Knowledge Graph Demo — Add facts, query entities, view timeline.

Usage:
    python examples/03_knowledge_graph.py /path/to/repo
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engramkit.storage.vault import VaultManager
from engramkit.graph.knowledge_graph import KnowledgeGraph


def main():
    if len(sys.argv) < 2:
        print("Usage: python examples/03_knowledge_graph.py /path/to/repo")
        sys.exit(1)

    repo_path = sys.argv[1]
    vault = VaultManager.get_vault(repo_path)
    kg = KnowledgeGraph(str(vault.vault_path / "knowledge_graph.sqlite3"))

    # Add some facts
    print("Adding facts...")
    kg.add_triple("EngramKit", "uses", "ChromaDB", valid_from="2026-04-09")
    kg.add_triple("EngramKit", "uses", "SQLite FTS5", valid_from="2026-04-09")
    kg.add_triple("EngramKit", "has_feature", "Hybrid Search", valid_from="2026-04-09")
    kg.add_triple("EngramKit", "replaces", "MemPalace", valid_from="2026-04-09")
    kg.add_triple("ChromaDB", "embeds_with", "all-MiniLM-L6-v2")

    # Query an entity
    print("\n=== Facts about EngramKit ===")
    facts = kg.query_entity("EngramKit")
    for f in facts:
        status = "current" if f["current"] else "expired"
        print(f"  {f['subject']} → {f['predicate']} → {f['object']}  ({status})")

    # Timeline
    print("\n=== Timeline ===")
    timeline = kg.timeline()
    for t in timeline:
        date = t["valid_from"] or "?"
        print(f"  [{date}] {t['subject']} → {t['predicate']} → {t['object']}")

    # Stats
    print("\n=== Stats ===")
    s = kg.stats()
    print(f"  Entities: {s['entities']}")
    print(f"  Triples: {s['triples']}")
    print(f"  Current: {s['current_facts']}")
    print(f"  Relationship types: {s['relationship_types']}")

    # Invalidate a fact
    print("\n--- Invalidating: EngramKit replaces MemPalace ---")
    kg.invalidate("EngramKit", "replaces", "MemPalace", ended="2026-12-31")
    facts = kg.query_entity("EngramKit")
    for f in facts:
        status = "current" if f["current"] else "expired"
        print(f"  {f['subject']} → {f['predicate']} → {f['object']}  ({status})")

    kg.close()
    vault.close()


if __name__ == "__main__":
    main()
