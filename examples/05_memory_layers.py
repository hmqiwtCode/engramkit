"""
Memory Layers Demo — Show L0 identity, L1 essential context, L2 recall.

Demonstrates token-budgeted context loading with recency scoring.

Usage:
    python examples/05_memory_layers.py /path/to/repo
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engramkit.config import ENGRAMKIT_HOME
from engramkit.storage.vault import VaultManager
from engramkit.memory.layers import MemoryStack
from engramkit.memory.token_budget import TokenBudget


def main():
    if len(sys.argv) < 2:
        print("Usage: python examples/05_memory_layers.py /path/to/repo")
        sys.exit(1)

    repo_path = sys.argv[1]
    vault = VaultManager.get_vault(repo_path)

    # Create identity if it doesn't exist
    identity_path = ENGRAMKIT_HOME / "identity.txt"
    if not identity_path.exists():
        identity_path.write_text("You are an AI assistant working on a software project.")
        print(f"Created identity at {identity_path}")

    # Configure budgets
    budget = TokenBudget(
        l0_max=100,    # Identity: 100 tokens
        l1_max=500,    # Essential: 500 tokens
        l2_max=1000,   # Recall: 1000 tokens
        l3_max=2000,   # Deep search: 2000 tokens
    )

    stack = MemoryStack(vault, budget)

    # L0 + L1 Wake-up
    print("=== Wake-Up (L0 + L1) ===")
    result = stack.wake_up()
    l0 = result["l0_report"]
    l1 = result["l1_report"]
    print(f"  L0: {l0.tokens_used}/{l0.tokens_budget} tokens ({l0.chunks_loaded} chunks)")
    print(f"  L1: {l1.tokens_used}/{l1.tokens_budget} tokens ({l1.chunks_loaded} chunks, {l1.chunks_skipped_dedup} deduped)")
    print(f"  Total: {result['total_tokens']} tokens")
    if result["text"]:
        print(f"\n  Context preview (first 300 chars):")
        print(f"  {result['text'][:300]}...")

    # L2 Recall
    print("\n=== Recall (L2) ===")
    recall = stack.recall(n_results=5)
    print(f"  Tokens: {recall['report'].tokens_used}/{budget.l2_max}")
    print(f"  Chunks: {recall['report'].chunks_loaded}")

    # L3 Deep Search
    print("\n=== Deep Search (L3) ===")
    query = "main entry point"
    search = stack.search(query, n_results=3)
    print(f"  Query: '{query}'")
    print(f"  Tokens: {search['report'].tokens_used}/{budget.l3_max}")
    print(f"  Results: {search['report'].chunks_loaded}")

    vault.close()


if __name__ == "__main__":
    main()
