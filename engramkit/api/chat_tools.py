"""In-process SDK MCP server for the chat endpoint.

Binds engramkit memory tools (search, recall, kg_query, etc.) to a set of vaults
so the chat agent can iteratively pull context instead of relying on a single
upfront hybrid search.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from engramkit.graph.knowledge_graph import KnowledgeGraph
from engramkit.ingest.chunker import content_hash
from engramkit.memory.layers import MemoryStack
from engramkit.memory.token_budget import TokenBudget, count_tokens
from engramkit.search.hybrid import hybrid_search
from engramkit.storage.vault import VaultManager


def _text(payload: Any) -> dict:
    body = payload if isinstance(payload, str) else json.dumps(payload, indent=2, default=str)
    return {"content": [{"type": "text", "text": body}]}


def _err(msg: str) -> dict:
    return {"content": [{"type": "text", "text": f"Error: {msg}"}], "is_error": True}


def _repo_label(path: str) -> str:
    return path.rstrip("/").split("/")[-1] or path


def build_engramkit_mcp_server(repo_paths: list[str]):
    """Return an `McpSdkServerConfig` with engramkit tools bound to `repo_paths`.

    Multi-vault aware: search / recall / status fan out across every vault;
    KG operations and wake_up target the first vault unless the model passes
    an explicit `repo_path`.
    """
    from claude_agent_sdk import SdkMcpTool, create_sdk_mcp_server

    primary = repo_paths[0] if repo_paths else None

    def _targets(repo_path: str | None) -> list[str]:
        if repo_path:
            return [repo_path]
        return list(repo_paths) if repo_paths else ([primary] if primary else [])

    def _open(path: str | None):
        return VaultManager.get_vault(path or primary)

    def _kg(vault):
        return KnowledgeGraph(str(vault.vault_path / "knowledge_graph.sqlite3"))

    async def h_search(args: dict[str, Any]) -> dict:
        query = (args.get("query") or "").strip()
        if not query:
            return _err("query is required")
        n = int(args.get("n_results") or 5)
        wing, room = args.get("wing"), args.get("room")
        hits: list[dict] = []
        for path in _targets(args.get("repo_path")):
            vault = VaultManager.get_vault(path)
            try:
                got = hybrid_search(query=query, vault=vault, n_results=n, wing=wing, room=room)
                label = _repo_label(path)
                for g in got:
                    g["_repo"] = label
                hits.extend(got)
            finally:
                vault.close()
        hits.sort(key=lambda x: x.get("score", 0), reverse=True)
        hits = hits[:n]
        return _text({"query": query, "count": len(hits), "results": hits})

    async def h_recall(args: dict[str, Any]) -> dict:
        wing, room = args.get("wing"), args.get("room")
        n = int(args.get("n_results") or 10)
        out = []
        for path in _targets(args.get("repo_path")):
            vault = VaultManager.get_vault(path)
            try:
                result = MemoryStack(vault).recall(wing=wing, room=room, n_results=n)
                out.append({
                    "repo": _repo_label(path),
                    "text": result["text"],
                    "tokens": result["report"].tokens_used,
                })
            finally:
                vault.close()
        return _text({"wing": wing, "room": room, "recalls": out})

    async def h_wake_up(args: dict[str, Any]) -> dict:
        vault = _open(args.get("repo_path"))
        try:
            budget = TokenBudget(l1_max=int(args.get("l1_tokens") or 1000))
            result = MemoryStack(vault, budget).wake_up(wing=args.get("wing"))
            return _text({
                "context": result["text"],
                "total_tokens": result["total_tokens"],
            })
        finally:
            vault.close()

    async def h_kg_query(args: dict[str, Any]) -> dict:
        entity = (args.get("entity") or "").strip()
        if not entity:
            return _err("entity is required")
        vault = _open(args.get("repo_path"))
        try:
            kg = _kg(vault)
            try:
                results = kg.query_entity(
                    entity,
                    as_of=args.get("as_of"),
                    direction=args.get("direction", "both"),
                )
            finally:
                kg.close()
            return _text({"entity": entity, "count": len(results), "facts": results})
        finally:
            vault.close()

    async def h_kg_timeline(args: dict[str, Any]) -> dict:
        vault = _open(args.get("repo_path"))
        try:
            kg = _kg(vault)
            try:
                results = kg.timeline(args.get("entity"))
            finally:
                kg.close()
            return _text({"count": len(results), "timeline": results})
        finally:
            vault.close()

    async def h_status(args: dict[str, Any]) -> dict:
        vaults = []
        for path in _targets(args.get("repo_path")):
            vault = VaultManager.get_vault(path)
            try:
                vaults.append({"repo": _repo_label(path), **vault.stats()})
            finally:
                vault.close()
        return _text({"vaults": vaults})

    async def h_save(args: dict[str, Any]) -> dict:
        text = args.get("content")
        if not text:
            return _err("content is required")
        vault = _open(args.get("repo_path"))
        try:
            chash = content_hash(text)
            wing = args.get("wing") or vault.get_meta("wing") or "default"
            vault.batch_upsert_chunks([{
                "content_hash": chash,
                "content": text,
                "file_path": "chat_save",
                "file_hash": chash,
                "wing": wing,
                "room": args.get("room", "general"),
                "generation": vault.current_generation(),
                "importance": float(args.get("importance", 3.0)),
                "is_secret": 0,
            }])
            return _text({"saved": True, "content_hash": chash, "tokens": count_tokens(text)})
        finally:
            vault.close()

    async def h_kg_add(args: dict[str, Any]) -> dict:
        subj, pred, obj = args.get("subject"), args.get("predicate"), args.get("object")
        if not (subj and pred and obj):
            return _err("subject, predicate, object are all required")
        vault = _open(args.get("repo_path"))
        try:
            kg = _kg(vault)
            try:
                tid = kg.add_triple(
                    subj, pred, obj,
                    valid_from=args.get("valid_from"),
                    valid_to=args.get("valid_to"),
                )
            finally:
                kg.close()
            return _text({"added": True, "triple_id": tid})
        finally:
            vault.close()

    async def h_diary(args: dict[str, Any]) -> dict:
        text = args.get("content")
        if not text:
            return _err("content is required")
        vault = _open(args.get("repo_path"))
        try:
            wing = args.get("wing") or "diary"
            entry = f"[{datetime.now().isoformat()}] {text}"
            chash = content_hash(entry)
            vault.batch_upsert_chunks([{
                "content_hash": chash,
                "content": entry,
                "file_path": "diary",
                "file_hash": chash,
                "wing": f"agent_{wing}",
                "room": "diary",
                "generation": vault.current_generation(),
                "importance": 2.0,
                "is_secret": 0,
            }])
            return _text({"saved": True, "content_hash": chash})
        finally:
            vault.close()

    tools = [
        SdkMcpTool(
            name="engramkit_search",
            description=(
                "Hybrid search (semantic + BM25) across the selected vaults. "
                "Call multiple times with different phrasings to triangulate — "
                "broad query first, then narrow with wing/room filters."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "n_results": {"type": "integer", "default": 5},
                    "wing": {"type": "string", "description": "Optional wing filter"},
                    "room": {"type": "string", "description": "Optional room filter"},
                    "repo_path": {"type": "string", "description": "Limit to one repo (default: all selected)"},
                },
                "required": ["query"],
            },
            handler=h_search,
        ),
        SdkMcpTool(
            name="engramkit_recall",
            description=(
                "L2 on-demand recall — recent chunks filtered by wing/room. "
                "Use when you know the topic area and want context by recency × importance "
                "rather than by query relevance."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "wing": {"type": "string"},
                    "room": {"type": "string"},
                    "n_results": {"type": "integer", "default": 10},
                    "repo_path": {"type": "string"},
                },
            },
            handler=h_recall,
        ),
        SdkMcpTool(
            name="engramkit_kg_query",
            description=(
                "Query the knowledge graph for entity relationships "
                "(subject→predicate→object triples). Supports temporal filtering with as_of."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "entity": {"type": "string"},
                    "as_of": {"type": "string", "description": "ISO date (YYYY-MM-DD)"},
                    "direction": {
                        "type": "string",
                        "enum": ["outgoing", "incoming", "both"],
                        "default": "both",
                    },
                    "repo_path": {"type": "string"},
                },
                "required": ["entity"],
            },
            handler=h_kg_query,
        ),
        SdkMcpTool(
            name="engramkit_kg_timeline",
            description="Chronological timeline of KG facts, optionally filtered by entity.",
            input_schema={
                "type": "object",
                "properties": {
                    "entity": {"type": "string", "description": "Entity name (omit for all)"},
                    "repo_path": {"type": "string"},
                },
            },
            handler=h_kg_timeline,
        ),
        SdkMcpTool(
            name="engramkit_wake_up",
            description=(
                "Load L0 identity + L1 essential context for a vault. "
                "Use at the start of complex multi-step questions."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "wing": {"type": "string"},
                    "l1_tokens": {"type": "integer", "default": 1000},
                    "repo_path": {"type": "string"},
                },
            },
            handler=h_wake_up,
        ),
        SdkMcpTool(
            name="engramkit_status",
            description="Vault overview stats across selected vaults.",
            input_schema={
                "type": "object",
                "properties": {"repo_path": {"type": "string"}},
            },
            handler=h_status,
        ),
        SdkMcpTool(
            name="engramkit_save",
            description=(
                "Save a key insight or decision to the vault for future recall. "
                "Use after reaching an important conclusion in the conversation."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "wing": {"type": "string"},
                    "room": {"type": "string", "default": "general"},
                    "importance": {"type": "number", "default": 3.0},
                    "repo_path": {"type": "string"},
                },
                "required": ["content"],
            },
            handler=h_save,
        ),
        SdkMcpTool(
            name="engramkit_kg_add",
            description="Add a fact (subject→predicate→object) to the knowledge graph.",
            input_schema={
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "predicate": {"type": "string"},
                    "object": {"type": "string"},
                    "valid_from": {"type": "string"},
                    "valid_to": {"type": "string"},
                    "repo_path": {"type": "string"},
                },
                "required": ["subject", "predicate", "object"],
            },
            handler=h_kg_add,
        ),
        SdkMcpTool(
            name="engramkit_diary_write",
            description="Write a diary entry (agent's journal) for session notes.",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "wing": {"type": "string"},
                    "repo_path": {"type": "string"},
                },
                "required": ["content"],
            },
            handler=h_diary,
        ),
    ]

    return create_sdk_mcp_server(name="engramkit", version="0.1.0", tools=tools)


ENGRAMKIT_TOOL_NAMES = [
    "mcp__engramkit__engramkit_search",
    "mcp__engramkit__engramkit_recall",
    "mcp__engramkit__engramkit_kg_query",
    "mcp__engramkit__engramkit_kg_timeline",
    "mcp__engramkit__engramkit_wake_up",
    "mcp__engramkit__engramkit_status",
    "mcp__engramkit__engramkit_save",
    "mcp__engramkit__engramkit_kg_add",
    "mcp__engramkit__engramkit_diary_write",
]
