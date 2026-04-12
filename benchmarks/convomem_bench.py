#!/usr/bin/env python3
"""
EngramKit × ConvoMem Benchmark
================================

Same benchmark as MemPalace uses (75,336 QA pairs from HuggingFace).
Tests THREE modes:
  1. raw       — ChromaDB semantic only (same as MemPalace "96.6%" mode)
  2. hybrid    — EngramKit hybrid search (semantic + BM25)
  3. bm25_only — SQLite FTS5 keyword search only

This lets us honestly compare what MemPalace measures vs what EngramKit adds.

Usage:
    python benchmarks/convomem_bench.py                    # 100 items, all modes
    python benchmarks/convomem_bench.py --limit 500        # 500 items
    python benchmarks/convomem_bench.py --mode hybrid      # hybrid only
"""

import os
import sys
import json
import shutil
import ssl
import tempfile
import argparse
import urllib.request
from pathlib import Path
from collections import defaultdict
from datetime import datetime

import chromadb

sys.path.insert(0, str(Path(__file__).parent.parent))

# Bypass SSL for restricted environments
ssl._create_default_https_context = ssl._create_unverified_context

HF_BASE = "https://huggingface.co/datasets/Salesforce/ConvoMem/resolve/main/core_benchmark/evidence_questions"

CATEGORIES = {
    "user_evidence": "User Facts",
    "assistant_facts_evidence": "Assistant Facts",
    "changing_evidence": "Changing Facts",
    "abstention_evidence": "Abstention",
    "preference_evidence": "Preferences",
    "implicit_connection_evidence": "Implicit Connections",
}


# ── Data loading (same as MemPalace) ────────────────────────────────────

def download_file(category, subpath, cache_dir):
    url = f"{HF_BASE}/{category}/{subpath}"
    cache_path = os.path.join(cache_dir, category, subpath.replace("/", "_"))
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            return json.load(f)
    try:
        urllib.request.urlretrieve(url, cache_path)
        with open(cache_path) as f:
            return json.load(f)
    except Exception as e:
        print(f"    Failed: {e}")
        return None


def discover_files(category, cache_dir):
    api_url = f"https://huggingface.co/api/datasets/Salesforce/ConvoMem/tree/main/core_benchmark/evidence_questions/{category}/1_evidence"
    cache_path = os.path.join(cache_dir, f"{category}_filelist.json")
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            return json.load(f)
    try:
        with urllib.request.urlopen(api_url, timeout=15) as resp:
            files = json.loads(resp.read())
            paths = [f["path"].split(f"{category}/")[1] for f in files if f["path"].endswith(".json")]
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, "w") as f:
                json.dump(paths, f)
            return paths
    except Exception:
        return []


def load_items(categories, limit, cache_dir):
    all_items = []
    for cat in categories:
        files = discover_files(cat, cache_dir)
        if not files:
            print(f"  Skipping {cat}")
            continue
        items = []
        for fpath in files:
            if len(items) >= limit:
                break
            data = download_file(cat, fpath, cache_dir)
            if data and "evidence_items" in data:
                for item in data["evidence_items"]:
                    item["_category"] = cat
                    items.append(item)
        all_items.extend(items[:limit])
        print(f"  {CATEGORIES.get(cat, cat)}: {len(items[:limit])} items")
    return all_items


# ── Retrieval functions ─────────────────────────────────────────────────

def retrieve_raw(corpus, question, top_k=10):
    """Mode: raw — pure ChromaDB semantic search (what MemPalace actually benchmarks)."""
    tmpdir = tempfile.mkdtemp(prefix="engramkit_bench_")
    try:
        client = chromadb.PersistentClient(path=os.path.join(tmpdir, "chroma"))
        col = client.create_collection("bench")
        col.add(
            documents=corpus,
            ids=[f"msg_{i}" for i in range(len(corpus))],
        )
        results = col.query(query_texts=[question], n_results=min(top_k, len(corpus)), include=["documents"])
        return [d.strip().lower() for d in results["documents"][0]]
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def retrieve_hybrid(corpus, question, top_k=10):
    """Mode: hybrid — EngramKit's semantic + BM25 search."""
    from engramkit.storage.vault import Vault
    from engramkit.search.hybrid import hybrid_search
    from engramkit.ingest.chunker import content_hash

    tmpdir = tempfile.mkdtemp(prefix="engramkit_bench_")
    try:
        vault = Vault(Path(tmpdir) / "vault")
        vault.open()

        chunks = []
        for i, doc in enumerate(corpus):
            chunks.append({
                "content_hash": content_hash(doc + str(i)),
                "content": doc,
                "file_path": f"msg_{i}.txt",
                "file_hash": content_hash(doc),
                "wing": "bench",
                "room": "general",
                "generation": 1,
                "is_secret": 0,
            })
        vault.batch_upsert_chunks(chunks)

        results = hybrid_search(question, vault, n_results=top_k)
        texts = [r["content"].strip().lower() for r in results]
        vault.close()
        return texts
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def retrieve_bm25(corpus, question, top_k=10):
    """Mode: bm25_only — SQLite FTS5 keyword search only."""
    from engramkit.storage.vault import Vault
    from engramkit.search.fts import fts_search
    from engramkit.ingest.chunker import content_hash

    tmpdir = tempfile.mkdtemp(prefix="engramkit_bench_")
    try:
        vault = Vault(Path(tmpdir) / "vault")
        vault.open()

        chunks = []
        for i, doc in enumerate(corpus):
            chunks.append({
                "content_hash": content_hash(doc + str(i)),
                "content": doc,
                "file_path": f"msg_{i}.txt",
                "file_hash": content_hash(doc),
                "wing": "bench",
                "room": "general",
                "generation": 1,
                "is_secret": 0,
            })
        vault.batch_upsert_chunks(chunks)

        results = fts_search(vault.conn, question, n_results=top_k)
        texts = [r["content"].strip().lower() for r in results]
        vault.close()
        return texts
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ── Scoring ─────────────────────────────────────────────────────────────

def score_retrieval(retrieved_texts, evidence_texts):
    found = 0
    for ev in evidence_texts:
        for ret in retrieved_texts:
            if ev in ret or ret in ev:
                found += 1
                break
    return found / len(evidence_texts) if evidence_texts else 1.0


# ── Main ────────────────────────────────────────────────────────────────

def run_benchmark(categories, limit, modes, top_k, cache_dir):
    print(f"\n{'=' * 60}")
    print("  EngramKit × ConvoMem Benchmark")
    print(f"{'=' * 60}")
    print(f"  Modes:       {', '.join(modes)}")
    print(f"  Limit/cat:   {limit}")
    print(f"  Top-k:       {top_k}")
    print(f"{'─' * 60}\n")

    items = load_items(categories, limit, cache_dir)
    print(f"\n  Total: {len(items)} items\n{'─' * 60}\n")

    RETRIEVE_FN = {
        "raw": retrieve_raw,
        "hybrid": retrieve_hybrid,
        "bm25_only": retrieve_bm25,
    }

    results = {mode: {"recalls": [], "per_cat": defaultdict(list)} for mode in modes}
    start = datetime.now()

    for i, item in enumerate(items):
        question = item["question"]
        evidence_texts = set(e["text"].strip().lower() for e in item.get("message_evidences", []))
        corpus = []
        for conv in item.get("conversations", []):
            for msg in conv.get("messages", []):
                corpus.append(msg["text"])

        if not corpus or not evidence_texts:
            continue

        for mode in modes:
            retrieved = RETRIEVE_FN[mode](corpus, question, top_k)
            recall = score_retrieval(retrieved, evidence_texts)
            results[mode]["recalls"].append(recall)
            results[mode]["per_cat"][item["_category"]].append(recall)

        if (i + 1) % 20 == 0 or i == len(items) - 1:
            summaries = []
            for mode in modes:
                r = results[mode]["recalls"]
                avg = sum(r) / len(r) if r else 0
                summaries.append(f"{mode}={avg:.3f}")
            print(f"  [{i+1:4}/{len(items)}] {' | '.join(summaries)}")

    elapsed = (datetime.now() - start).total_seconds()

    # Results
    print(f"\n{'=' * 60}")
    print(f"  RESULTS (top-{top_k})")
    print(f"{'=' * 60}")
    print(f"  Time: {elapsed:.1f}s ({elapsed / max(len(items), 1):.2f}s/item)\n")

    print(f"  {'Mode':<12} {'Avg R@k':>8} {'Perfect':>8} {'Zero':>8}")
    print(f"  {'─'*40}")
    for mode in modes:
        r = results[mode]["recalls"]
        avg = sum(r) / len(r) if r else 0
        perfect = sum(1 for x in r if x >= 1.0)
        zero = sum(1 for x in r if x == 0)
        print(f"  {mode:<12} {avg:>8.3f} {perfect:>7}/{len(r)} {zero:>7}/{len(r)}")

    print(f"\n  PER-CATEGORY:")
    for cat in sorted(set(item["_category"] for item in items)):
        print(f"\n  {CATEGORIES.get(cat, cat)}:")
        for mode in modes:
            vals = results[mode]["per_cat"][cat]
            avg = sum(vals) / len(vals) if vals else 0
            print(f"    {mode:<12} R={avg:.3f}  ({sum(1 for v in vals if v >= 1.0)}/{len(vals)} perfect)")

    print(f"\n{'=' * 60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EngramKit × ConvoMem Benchmark")
    parser.add_argument("--limit", type=int, default=100, help="Items per category")
    parser.add_argument("--top-k", type=int, default=10, help="Top-k retrieval")
    parser.add_argument("--mode", choices=["raw", "hybrid", "bm25_only", "all"], default="all")
    parser.add_argument("--cache-dir", default="/tmp/convomem_cache")
    args = parser.parse_args()

    modes = ["raw", "hybrid", "bm25_only"] if args.mode == "all" else [args.mode]
    cats = list(CATEGORIES.keys())
    run_benchmark(cats, args.limit, modes, args.top_k, args.cache_dir)
