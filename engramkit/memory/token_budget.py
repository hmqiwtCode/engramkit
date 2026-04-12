"""Token budget manager — real counting, recency scoring, deduplication."""

import math
from datetime import datetime
from dataclasses import dataclass, field

import tiktoken

# Use cl100k_base (GPT-4/Claude compatible tokenizer)
_encoder = None


def _get_encoder():
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding("cl100k_base")
    return _encoder


def count_tokens(text: str) -> int:
    """Exact token count using tiktoken."""
    return len(_get_encoder().encode(text))


@dataclass
class TokenBudget:
    """Configurable per-layer token budgets."""
    l0_max: int = 150
    l1_max: int = 1000
    l2_max: int = 2000
    l3_max: int = 4000


@dataclass
class BudgetReport:
    """Token usage report after context loading."""
    layer: str
    tokens_used: int
    tokens_budget: int
    chunks_loaded: int
    chunks_skipped_dedup: int = 0
    chunks_skipped_budget: int = 0


def score_chunk(chunk: dict, now: datetime = None) -> float:
    """
    Combined score: importance * recency_decay + access_boost.

    - importance: 1-5 scale (default 3)
    - recency: exponential decay, half-life ~7 days
    - access_boost: log of access count
    """
    if now is None:
        now = datetime.now()

    importance = float(chunk.get("importance", 3.0))

    # Recency decay
    updated = chunk.get("updated_at") or chunk.get("created_at", "")
    if updated:
        try:
            updated_dt = datetime.fromisoformat(updated)
            age_days = max(0, (now - updated_dt).total_seconds() / 86400)
            recency = math.exp(-0.1 * age_days)  # ~0.5 at 7 days
        except (ValueError, TypeError):
            recency = 0.5
    else:
        recency = 0.5

    # Access frequency boost
    access_count = int(chunk.get("access_count", 0))
    access_boost = math.log1p(access_count) * 0.2

    return importance * recency + access_boost


def deduplicate_chunks(chunks: list[dict], threshold: float = 0.85) -> list[dict]:
    """
    Remove near-duplicate chunks by comparing content prefixes.
    Uses first 200 chars as a fast similarity proxy.
    """
    selected = []
    seen_prefixes = set()

    for chunk in chunks:
        prefix = chunk.get("content", "")[:200].strip().lower()
        # Check if any existing prefix is very similar
        is_dup = False
        for existing in seen_prefixes:
            if _prefix_similarity(prefix, existing) > threshold:
                is_dup = True
                break
        if not is_dup:
            selected.append(chunk)
            seen_prefixes.add(prefix)

    return selected


def _prefix_similarity(a: str, b: str) -> float:
    """Quick character-level similarity for dedup (Jaccard on char trigrams)."""
    if not a or not b:
        return 0.0
    trigrams_a = {a[i:i+3] for i in range(len(a) - 2)} if len(a) >= 3 else {a}
    trigrams_b = {b[i:i+3] for i in range(len(b) - 2)} if len(b) >= 3 else {b}
    if not trigrams_a or not trigrams_b:
        return 0.0
    intersection = trigrams_a & trigrams_b
    union = trigrams_a | trigrams_b
    return len(intersection) / len(union)


def select_within_budget(
    chunks: list[dict],
    max_tokens: int,
    deduplicate: bool = True,
) -> tuple[list[dict], BudgetReport]:
    """
    Select top-scored chunks that fit within token budget.

    1. Score all chunks by recency + importance
    2. Sort descending
    3. Deduplicate near-duplicates
    4. Fill budget greedily
    """
    now = datetime.now()

    # Score and sort
    scored = [(score_chunk(c, now), c) for c in chunks]
    scored.sort(key=lambda x: x[0], reverse=True)

    # Deduplicate
    dedup_skipped = 0
    if deduplicate:
        before = len(scored)
        candidates = deduplicate_chunks([c for _, c in scored])
        dedup_skipped = before - len(candidates)
        # Re-score after dedup (maintain order)
        scored_map = {c.get("content_hash", id(c)): s for s, c in scored}
        candidates_scored = [
            (scored_map.get(c.get("content_hash", id(c)), 0), c)
            for c in candidates
        ]
    else:
        candidates_scored = scored

    # Fill within budget
    selected = []
    tokens_used = 0
    budget_skipped = 0

    for score, chunk in candidates_scored:
        content = chunk.get("content", "")
        chunk_tokens = count_tokens(content)
        if tokens_used + chunk_tokens <= max_tokens:
            selected.append(chunk)
            tokens_used += chunk_tokens
        else:
            budget_skipped += 1

    report = BudgetReport(
        layer="",
        tokens_used=tokens_used,
        tokens_budget=max_tokens,
        chunks_loaded=len(selected),
        chunks_skipped_dedup=dedup_skipped,
        chunks_skipped_budget=budget_skipped,
    )

    return selected, report
