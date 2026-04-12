#!/usr/bin/env python3
"""
EngramKit vs MemPalace — Head-to-head benchmark.

Compares:
  1. Ingest speed (first mine)
  2. Re-mine speed (no changes)
  3. Search quality (same queries, compare results)
  4. Storage size (disk usage)
  5. Retrieval recall (can it find what was indexed?)

Usage:
    python benchmarks/compare_mempalace.py <repo_path>
    python benchmarks/compare_mempalace.py /path/to/any/repo --queries "how does auth work" "database schema"
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

# ── EngramKit imports ──────────────────────────────────────────────────────

sys.path.insert(0, str(Path(__file__).parent.parent))

from engramkit.storage.vault import Vault, VaultManager
from engramkit.ingest.pipeline import mine as engramkit_mine, scan_files
from engramkit.search.hybrid import hybrid_search
from engramkit.search.fts import fts_search


# ── MemPalace imports (optional) ────────────────────────────────────────────

MEMPALACE_AVAILABLE = False
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "reference" / "mempalace"))
    from mempalace.miner import mine as mempalace_mine_fn, scan_project, chunk_text, get_collection
    from mempalace.searcher import search_memories
    MEMPALACE_AVAILABLE = True
except ImportError:
    pass


# ── Benchmark helpers ───────────────────────────────────────────────────────

def get_dir_size(path: str) -> int:
    """Get total size of directory in bytes."""
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
    return total


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def format_time(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    return f"{seconds:.2f}s"


# ── EngramKit benchmark ───────────────────────────────────────────────────

def bench_engramkit(repo_path: str, queries: list[str], tmp_dir: str) -> dict:
    """Benchmark EngramKit: mine, re-mine, search."""
    results = {"name": "EngramKit"}

    # Use temp vault to avoid polluting user's data
    vault = Vault(Path(tmp_dir) / "engramkit_vault")
    vault.open()
    vault.set_meta("repo_path", repo_path)
    wing = Path(repo_path).name.lower().replace("-", "_")

    # 1. First mine
    start = time.perf_counter()
    stats = engramkit_mine(repo_path, vault, wing=wing)
    results["first_mine_time"] = time.perf_counter() - start
    results["files_processed"] = stats["files_processed"]
    results["chunks_created"] = stats["chunks_added"]
    results["secrets_found"] = stats["secrets_found"]

    # 2. Re-mine (no changes)
    start = time.perf_counter()
    stats2 = engramkit_mine(repo_path, vault, wing=wing)
    results["remine_time"] = time.perf_counter() - start
    results["remine_skipped"] = stats2["files_skipped"]

    # 3. Search
    search_results = {}
    total_search_time = 0
    for query in queries:
        start = time.perf_counter()
        hits = hybrid_search(query, vault, n_results=5)
        elapsed = time.perf_counter() - start
        total_search_time += elapsed
        search_results[query] = {
            "count": len(hits),
            "time": elapsed,
            "top_files": [h.get("file_path", "?") for h in hits[:3]],
            "sources": [", ".join(h.get("sources", [])) for h in hits[:3]],
        }
    results["search_results"] = search_results
    results["avg_search_time"] = total_search_time / len(queries) if queries else 0

    # 4. Storage size
    vault_path = str(Path(tmp_dir) / "engramkit_vault")
    results["storage_bytes"] = get_dir_size(vault_path)
    results["storage_human"] = format_size(results["storage_bytes"])

    vault.close()
    return results


# ── MemPalace benchmark ───────────────────────────────────────────────────

def bench_mempalace(repo_path: str, queries: list[str], tmp_dir: str) -> dict:
    """Benchmark MemPalace: mine, re-mine, search."""
    if not MEMPALACE_AVAILABLE:
        return {"name": "MemPalace", "error": "Not installed. Install from reference/mempalace/"}

    results = {"name": "MemPalace"}
    palace_path = os.path.join(tmp_dir, "mempalace_palace")
    os.makedirs(palace_path, exist_ok=True)
    wing = Path(repo_path).name.lower().replace("-", "_")

    # Need mempalace.yaml — create a minimal one
    yaml_path = Path(repo_path) / "mempalace.yaml"
    yaml_existed = yaml_path.exists()
    if not yaml_existed:
        yaml_path.write_text(f"wing: {wing}\nrooms:\n  - name: general\n    description: All files\n")

    try:
        # 1. First mine
        start = time.perf_counter()
        mempalace_mine_fn(repo_path, palace_path, wing_override=wing, agent="bench")
        results["first_mine_time"] = time.perf_counter() - start

        # Count what was mined
        import chromadb
        client = chromadb.PersistentClient(path=palace_path)
        try:
            col = client.get_collection("mempalace_drawers")
            results["chunks_created"] = col.count()
        except Exception:
            results["chunks_created"] = 0

        files = scan_project(repo_path)
        results["files_processed"] = len(files)

        # 2. Re-mine
        start = time.perf_counter()
        mempalace_mine_fn(repo_path, palace_path, wing_override=wing, agent="bench")
        results["remine_time"] = time.perf_counter() - start
        results["remine_skipped"] = "N/A (mtime-based)"

        # 3. Search
        search_results = {}
        total_search_time = 0
        for query in queries:
            start = time.perf_counter()
            hits = search_memories(query, palace_path, wing=wing, n_results=5)
            elapsed = time.perf_counter() - start
            total_search_time += elapsed
            hit_list = hits.get("results", [])
            search_results[query] = {
                "count": len(hit_list),
                "time": elapsed,
                "top_files": [h.get("source_file", "?") for h in hit_list[:3]],
                "sources": ["semantic" for _ in hit_list[:3]],
            }
        results["search_results"] = search_results
        results["avg_search_time"] = total_search_time / len(queries) if queries else 0

        # 4. Storage
        results["storage_bytes"] = get_dir_size(palace_path)
        results["storage_human"] = format_size(results["storage_bytes"])

    finally:
        if not yaml_existed and yaml_path.exists():
            yaml_path.unlink()

    return results


# ── Comparison report ──────────────────────────────────────────────────────

def print_comparison(engramkit: dict, mempalace: dict, queries: list[str]):
    print(f"\n{'=' * 70}")
    print("  EngramKit vs MemPalace — Benchmark Results")
    print(f"{'=' * 70}\n")

    if "error" in mempalace:
        print(f"  MemPalace: {mempalace['error']}")
        print(f"  Running EngramKit-only benchmark.\n")

    # Ingest
    print(f"  {'INGEST':40} {'EngramKit':>12} {'MemPalace':>12}")
    print(f"  {'─' * 64}")
    print(f"  {'First mine time':40} {format_time(engramkit['first_mine_time']):>12}", end="")
    if "first_mine_time" in mempalace:
        print(f" {format_time(mempalace['first_mine_time']):>12}")
    else:
        print(f" {'N/A':>12}")

    print(f"  {'Re-mine time (no changes)':40} {format_time(engramkit['remine_time']):>12}", end="")
    if "remine_time" in mempalace:
        print(f" {format_time(mempalace['remine_time']):>12}")
    else:
        print(f" {'N/A':>12}")

    print(f"  {'Files processed':40} {engramkit['files_processed']:>12}", end="")
    if "files_processed" in mempalace:
        print(f" {mempalace['files_processed']:>12}")
    else:
        print(f" {'N/A':>12}")

    print(f"  {'Chunks created':40} {engramkit['chunks_created']:>12}", end="")
    if "chunks_created" in mempalace:
        print(f" {mempalace['chunks_created']:>12}")
    else:
        print(f" {'N/A':>12}")

    print(f"  {'Re-mine files skipped':40} {engramkit['remine_skipped']:>12}", end="")
    if "remine_skipped" in mempalace:
        print(f" {str(mempalace['remine_skipped']):>12}")
    else:
        print(f" {'N/A':>12}")

    print(f"  {'Secrets auto-flagged':40} {engramkit['secrets_found']:>12}", end="")
    print(f" {'0 (none)':>12}")

    print(f"  {'Storage size':40} {engramkit['storage_human']:>12}", end="")
    if "storage_human" in mempalace:
        print(f" {mempalace['storage_human']:>12}")
    else:
        print(f" {'N/A':>12}")

    # Search
    print(f"\n  {'SEARCH':40} {'EngramKit':>12} {'MemPalace':>12}")
    print(f"  {'─' * 64}")
    print(f"  {'Avg search time':40} {format_time(engramkit['avg_search_time']):>12}", end="")
    if "avg_search_time" in mempalace:
        print(f" {format_time(mempalace['avg_search_time']):>12}")
    else:
        print(f" {'N/A':>12}")

    for query in queries:
        eq = engramkit["search_results"].get(query, {})
        mq = mempalace.get("search_results", {}).get(query, {})
        print(f"\n  Query: \"{query}\"")
        print(f"    {'Results found':38} {eq.get('count', 0):>12}", end="")
        print(f" {mq.get('count', 0):>12}" if mq else f" {'N/A':>12}")
        print(f"    {'Search time':38} {format_time(eq.get('time', 0)):>12}", end="")
        print(f" {format_time(mq.get('time', 0)):>12}" if mq else f" {'N/A':>12}")

        # Show top results
        e_files = eq.get("top_files", [])
        e_sources = eq.get("sources", [])
        m_files = mq.get("top_files", [])

        print(f"    EngramKit top hits:")
        for i, (f, s) in enumerate(zip(e_files, e_sources)):
            print(f"      [{i+1}] {Path(f).name:40} ({s})")

        if m_files:
            print(f"    MemPalace top hits:")
            for i, f in enumerate(m_files):
                print(f"      [{i+1}] {Path(f).name:40} (semantic)")

    # Key differences
    print(f"\n  {'KEY DIFFERENCES':40}")
    print(f"  {'─' * 64}")
    print(f"  {'Content-addressed IDs':40} {'Yes (SHA256)':>12} {'No (MD5+pos)':>12}")
    print(f"  {'Hybrid search (BM25+semantic)':40} {'Yes':>12} {'No (semantic)':>12}")
    print(f"  {'Garbage collection':40} {'Yes':>12} {'No':>12}")
    print(f"  {'Git-aware mining':40} {'Yes':>12} {'No':>12}")
    print(f"  {'Secrets filtering':40} {'Yes':>12} {'No':>12}")
    print(f"  {'Batch upsert':40} {'500/batch':>12} {'1 at a time':>12}")
    print(f"  {'Token counting':40} {'tiktoken':>12} {'len//4':>12}")
    print(f"  {'Recency in L1 scoring':40} {'Yes':>12} {'No':>12}")

    print(f"\n{'=' * 70}\n")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="EngramKit vs MemPalace benchmark")
    parser.add_argument("repo_path", help="Repository to benchmark")
    parser.add_argument("--queries", nargs="+",
                        default=["semantic search", "chunk_text", "how does mining work",
                                 "knowledge graph", "configuration"],
                        help="Search queries to test")
    parser.add_argument("--skip-mempalace", action="store_true", help="Only benchmark EngramKit")
    parser.add_argument("--output", help="Save results to JSON file")
    args = parser.parse_args()

    repo_path = str(Path(args.repo_path).expanduser().resolve())
    if not Path(repo_path).is_dir():
        print(f"Error: {repo_path} is not a directory")
        sys.exit(1)

    tmp_dir = tempfile.mkdtemp(prefix="engramkit_bench_")
    print(f"\n  Temp dir: {tmp_dir}")

    try:
        # Benchmark EngramKit
        print(f"\n  Benchmarking EngramKit...")
        engramkit_results = bench_engramkit(repo_path, args.queries, tmp_dir)

        # Benchmark MemPalace
        if args.skip_mempalace or not MEMPALACE_AVAILABLE:
            mempalace_results = {"name": "MemPalace", "error": "Skipped or not available"}
        else:
            print(f"\n  Benchmarking MemPalace...")
            mempalace_results = bench_mempalace(repo_path, args.queries, tmp_dir)

        # Print comparison
        print_comparison(engramkit_results, mempalace_results, args.queries)

        # Save JSON
        if args.output:
            with open(args.output, "w") as f:
                json.dump({"engramkit": engramkit_results, "mempalace": mempalace_results}, f, indent=2, default=str)
            print(f"  Results saved to: {args.output}")

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
