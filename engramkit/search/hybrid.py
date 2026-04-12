"""Hybrid search — semantic + BM25 with Reciprocal Rank Fusion."""

from engramkit.search.fts import fts_search
from engramkit.storage.vault import Vault


def hybrid_search(
    query: str,
    vault: Vault,
    n_results: int = 5,
    wing: str = None,
    room: str = None,
    semantic_weight: float = 0.7,
    lexical_weight: float = 0.3,
) -> list[dict]:
    """
    Hybrid search combining semantic (ChromaDB) and lexical (FTS5 BM25) results.
    Fused with Reciprocal Rank Fusion, deduplicated by content_hash.
    """
    fetch_n = n_results * 3  # Over-fetch for better fusion

    # 1. Semantic search via ChromaDB
    where = {}
    if wing and room:
        where = {"$and": [{"wing": wing}, {"room": room}]}
    elif wing:
        where = {"wing": wing}
    elif room:
        where = {"room": room}

    semantic_results = vault.chroma.search(
        query=query,
        n_results=fetch_n,
        where=where if where else None,
    )
    # Normalize: add source tag
    for r in semantic_results:
        r["source"] = "semantic"
        r["similarity"] = round(1 - r.get("distance", 1), 4)

    # 2. Lexical search via FTS5
    lexical_results = fts_search(
        conn=vault.conn,
        query=query,
        n_results=fetch_n,
        wing=wing,
        room=room,
    )
    for r in lexical_results:
        r["source"] = "lexical"
        r["similarity"] = 0.0  # FTS5 uses rank, not similarity

    # 3. Reciprocal Rank Fusion
    fused = _rrf_merge(
        [semantic_results, lexical_results],
        [semantic_weight, lexical_weight],
    )

    # 4. Deduplicate by content_hash
    seen = set()
    deduped = []
    for r in fused:
        h = r["content_hash"]
        if h not in seen:
            seen.add(h)
            deduped.append(r)

    # 5. Enrich with metadata from SQLite
    enriched = []
    for r in deduped[:n_results]:
        row = vault.conn.execute(
            """SELECT content, file_path, wing, room, importance, created_at,
                      git_commit, git_branch
               FROM chunks WHERE content_hash = ? AND is_stale = 0 AND is_secret = 0""",
            (r["content_hash"],),
        ).fetchone()
        if row:
            enriched.append({
                "content_hash": r["content_hash"],
                "content": row["content"],
                "file_path": row["file_path"],
                "wing": row["wing"],
                "room": row["room"],
                "importance": row["importance"],
                "created_at": row["created_at"],
                "git_commit": row["git_commit"],
                "git_branch": row["git_branch"],
                "score": r["score"],
                "sources": r.get("sources", [r.get("source", "unknown")]),
            })

            # Update access stats
            vault.conn.execute(
                """UPDATE chunks SET last_accessed = datetime('now'),
                          access_count = access_count + 1
                   WHERE content_hash = ?""",
                (r["content_hash"],),
            )
        vault.conn.commit()

    return enriched


def _rrf_merge(result_lists: list[list], weights: list[float], k: int = 60) -> list[dict]:
    """
    Reciprocal Rank Fusion — merge multiple ranked lists.
    score(d) = sum(weight_i / (k + rank_i + 1)) for each list containing d.
    """
    scores = {}
    for results, weight in zip(result_lists, weights):
        for rank, result in enumerate(results):
            key = result["content_hash"]
            if key not in scores:
                scores[key] = {
                    "content_hash": key,
                    "content": result.get("content", ""),
                    "score": 0.0,
                    "sources": [],
                }
            scores[key]["score"] += weight / (k + rank + 1)
            source = result.get("source", "unknown")
            if source not in scores[key]["sources"]:
                scores[key]["sources"].append(source)

    ranked = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
    return ranked
