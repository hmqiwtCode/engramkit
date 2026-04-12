"""EngramKit MCP Server — 12 tools for AI assistant integration."""

import json
import sys
from pathlib import Path
from datetime import datetime

from engramkit.config import ENGRAMKIT_HOME
from engramkit.storage.vault import Vault, VaultManager
from engramkit.search.hybrid import hybrid_search
from engramkit.memory.layers import MemoryStack
from engramkit.memory.token_budget import TokenBudget, count_tokens
from engramkit.graph.knowledge_graph import KnowledgeGraph
from engramkit.ingest.chunker import content_hash


# ── Tool Definitions ────────────────────────────────────────────────────────

TOOLS = [
    # Read tools
    {
        "name": "engramkit_status",
        "description": "Get vault overview: total chunks, wings, rooms, generation, stale/secret counts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Repository path (default: cwd)"},
            },
        },
    },
    {
        "name": "engramkit_search",
        "description": "Hybrid search (semantic + BM25) across the vault. Returns verbatim code/text chunks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "repo_path": {"type": "string"},
                "wing": {"type": "string", "description": "Filter by wing"},
                "room": {"type": "string", "description": "Filter by room"},
                "n_results": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "engramkit_wake_up",
        "description": "Load L0 (identity) + L1 (essential context) for session start. Token-budgeted.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string"},
                "wing": {"type": "string"},
                "l1_tokens": {"type": "integer", "default": 1000},
            },
        },
    },
    {
        "name": "engramkit_recall",
        "description": "L2 on-demand recall — retrieve recent chunks filtered by wing/room.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string"},
                "wing": {"type": "string"},
                "room": {"type": "string"},
                "n_results": {"type": "integer", "default": 10},
            },
        },
    },
    {
        "name": "engramkit_kg_query",
        "description": "Query knowledge graph for entity relationships, optionally filtered by date.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity": {"type": "string", "description": "Entity name to query"},
                "repo_path": {"type": "string"},
                "as_of": {"type": "string", "description": "Date filter (YYYY-MM-DD)"},
                "direction": {"type": "string", "enum": ["outgoing", "incoming", "both"], "default": "both"},
            },
            "required": ["entity"],
        },
    },
    {
        "name": "engramkit_kg_timeline",
        "description": "Chronological timeline of knowledge graph facts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity": {"type": "string", "description": "Entity name (optional, omit for all)"},
                "repo_path": {"type": "string"},
            },
        },
    },
    # Write tools
    {
        "name": "engramkit_save",
        "description": "Save content to the vault. Auto-generates content hash for dedup.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Text to save"},
                "repo_path": {"type": "string"},
                "wing": {"type": "string"},
                "room": {"type": "string", "default": "general"},
                "importance": {"type": "number", "default": 3.0},
            },
            "required": ["content"],
        },
    },
    {
        "name": "engramkit_kg_add",
        "description": "Add a fact to the knowledge graph: subject → predicate → object.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "predicate": {"type": "string"},
                "object": {"type": "string"},
                "repo_path": {"type": "string"},
                "valid_from": {"type": "string"},
                "valid_to": {"type": "string"},
            },
            "required": ["subject", "predicate", "object"],
        },
    },
    {
        "name": "engramkit_kg_invalidate",
        "description": "Mark a knowledge graph fact as no longer valid.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "predicate": {"type": "string"},
                "object": {"type": "string"},
                "repo_path": {"type": "string"},
                "ended": {"type": "string", "description": "End date (default: today)"},
            },
            "required": ["subject", "predicate", "object"],
        },
    },
    {
        "name": "engramkit_diary_write",
        "description": "Write a diary entry (agent's personal journal).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Diary entry text"},
                "repo_path": {"type": "string"},
                "wing": {"type": "string"},
            },
            "required": ["content"],
        },
    },
    # Admin tools
    {
        "name": "engramkit_gc",
        "description": "Run garbage collection to remove stale chunks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string"},
                "retention_days": {"type": "integer", "default": 30},
            },
        },
    },
    {
        "name": "engramkit_config",
        "description": "Get or set vault configuration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string"},
                "key": {"type": "string", "description": "Config key to get/set"},
                "value": {"type": "string", "description": "Value to set (omit to get)"},
            },
            "required": ["key"],
        },
    },
]


# ── Tool Handlers ───────────────────────────────────────────────────────────

def _get_vault(params: dict) -> tuple[Vault, str]:
    repo_path = params.get("repo_path") or str(Path.cwd())
    vault = VaultManager.get_vault(repo_path)
    return vault, repo_path


def _get_kg(vault: Vault) -> KnowledgeGraph:
    kg_path = str(vault.vault_path / "knowledge_graph.sqlite3")
    return KnowledgeGraph(kg_path)


ENGRAMKIT_PROTOCOL = """IMPORTANT — EngramKit Memory Protocol:

1. ON SESSION START: Call engramkit_wake_up to load L0 (identity) + L1 (essential context).
   This gives you ~170 tokens of who you are and recent important decisions/context.

2. BEFORE ANSWERING about code, architecture, or past decisions:
   Call engramkit_search with a relevant query. Never guess — verify from the vault.
   The hybrid search combines semantic understanding + keyword matching.

3. WHEN WORKING ON A SPECIFIC TOPIC:
   Call engramkit_recall with wing/room filters to get all context about that topic.

4. IF UNSURE about a fact or relationship:
   Call engramkit_kg_query to check the knowledge graph. Facts have temporal validity.

5. AFTER IMPORTANT DISCUSSIONS:
   Call engramkit_save to store key decisions, architecture changes, or insights.
   Call engramkit_diary_write for session notes.

6. WHEN FACTS CHANGE:
   Call engramkit_kg_invalidate on the old fact, engramkit_kg_add for the new one.

Layer summary:
  L0 (identity, ~100 tokens) — always loaded via wake_up
  L1 (essential, ~800 tokens) — top chunks by recency × importance, loaded via wake_up
  L2 (on-demand, ~2000 tokens) — topic-filtered chunks, loaded via recall
  L3 (deep search, unlimited) — hybrid search across full vault, loaded via search

This protocol ensures the AI KNOWS before it speaks."""


def handle_status(params: dict) -> dict:
    vault, _ = _get_vault(params)
    try:
        stats = vault.stats()
        stats["protocol"] = ENGRAMKIT_PROTOCOL
        return stats
    finally:
        vault.close()


def handle_search(params: dict) -> dict:
    vault, _ = _get_vault(params)
    try:
        results = hybrid_search(
            query=params["query"], vault=vault,
            n_results=params.get("n_results", 5),
            wing=params.get("wing"), room=params.get("room"),
        )
        return {"query": params["query"], "results": results, "count": len(results)}
    finally:
        vault.close()


def handle_wake_up(params: dict) -> dict:
    vault, _ = _get_vault(params)
    try:
        budget = TokenBudget(l1_max=params.get("l1_tokens", 1000))
        stack = MemoryStack(vault, budget)
        result = stack.wake_up(wing=params.get("wing"))
        return {
            "context": result["text"],
            "total_tokens": result["total_tokens"],
            "l0": {"tokens": result["l0_report"].tokens_used, "budget": result["l0_report"].tokens_budget},
            "l1": {"tokens": result["l1_report"].tokens_used, "budget": result["l1_report"].tokens_budget,
                    "loaded": result["l1_report"].chunks_loaded, "deduped": result["l1_report"].chunks_skipped_dedup},
            "protocol": ENGRAMKIT_PROTOCOL,
        }
    finally:
        vault.close()


def handle_recall(params: dict) -> dict:
    vault, _ = _get_vault(params)
    try:
        stack = MemoryStack(vault)
        result = stack.recall(
            wing=params.get("wing"), room=params.get("room"),
            n_results=params.get("n_results", 10),
        )
        return {"text": result["text"], "tokens": result["report"].tokens_used,
                "chunks_loaded": result["report"].chunks_loaded}
    finally:
        vault.close()


def handle_kg_query(params: dict) -> dict:
    vault, _ = _get_vault(params)
    try:
        kg = _get_kg(vault)
        results = kg.query_entity(
            params["entity"], as_of=params.get("as_of"),
            direction=params.get("direction", "both"),
        )
        kg.close()
        return {"entity": params["entity"], "facts": results, "count": len(results)}
    finally:
        vault.close()


def handle_kg_timeline(params: dict) -> dict:
    vault, _ = _get_vault(params)
    try:
        kg = _get_kg(vault)
        results = kg.timeline(params.get("entity"))
        kg.close()
        return {"timeline": results, "count": len(results)}
    finally:
        vault.close()


def handle_save(params: dict) -> dict:
    vault, _ = _get_vault(params)
    try:
        text = params["content"]
        chash = content_hash(text)
        wing = params.get("wing") or vault.get_meta("wing") or "default"
        chunk = {
            "content_hash": chash, "content": text,
            "file_path": "mcp_save", "file_hash": chash,
            "wing": wing, "room": params.get("room", "general"),
            "generation": vault.current_generation(),
            "importance": params.get("importance", 3.0),
            "is_secret": 0,
        }
        vault.batch_upsert_chunks([chunk])
        return {"saved": True, "content_hash": chash, "tokens": count_tokens(text)}
    finally:
        vault.close()


def handle_kg_add(params: dict) -> dict:
    vault, _ = _get_vault(params)
    try:
        kg = _get_kg(vault)
        triple_id = kg.add_triple(
            params["subject"], params["predicate"], params["object"],
            valid_from=params.get("valid_from"), valid_to=params.get("valid_to"),
        )
        kg.close()
        return {"added": True, "triple_id": triple_id}
    finally:
        vault.close()


def handle_kg_invalidate(params: dict) -> dict:
    vault, _ = _get_vault(params)
    try:
        kg = _get_kg(vault)
        kg.invalidate(params["subject"], params["predicate"], params["object"],
                      ended=params.get("ended"))
        kg.close()
        return {"invalidated": True}
    finally:
        vault.close()


def handle_diary_write(params: dict) -> dict:
    vault, _ = _get_vault(params)
    try:
        text = params["content"]
        wing = params.get("wing") or "diary"
        now = datetime.now().isoformat()
        entry = f"[{now}] {text}"
        chash = content_hash(entry)
        chunk = {
            "content_hash": chash, "content": entry,
            "file_path": "diary", "file_hash": chash,
            "wing": f"agent_{wing}", "room": "diary",
            "generation": vault.current_generation(),
            "importance": 2.0, "is_secret": 0,
        }
        vault.batch_upsert_chunks([chunk])
        return {"saved": True, "content_hash": chash}
    finally:
        vault.close()


def handle_gc(params: dict) -> dict:
    from engramkit.storage.gc import run_gc
    vault, _ = _get_vault(params)
    try:
        run_gc(vault, retention_days=params.get("retention_days", 30))
        return {"completed": True}
    finally:
        vault.close()


def handle_config(params: dict) -> dict:
    vault, _ = _get_vault(params)
    try:
        key = params["key"]
        value = params.get("value")
        if value is not None:
            vault.set_meta(key, value)
            return {"set": True, "key": key, "value": value}
        else:
            val = vault.get_meta(key)
            return {"key": key, "value": val}
    finally:
        vault.close()


HANDLERS = {
    "engramkit_status": handle_status,
    "engramkit_search": handle_search,
    "engramkit_wake_up": handle_wake_up,
    "engramkit_recall": handle_recall,
    "engramkit_kg_query": handle_kg_query,
    "engramkit_kg_timeline": handle_kg_timeline,
    "engramkit_save": handle_save,
    "engramkit_kg_add": handle_kg_add,
    "engramkit_kg_invalidate": handle_kg_invalidate,
    "engramkit_diary_write": handle_diary_write,
    "engramkit_gc": handle_gc,
    "engramkit_config": handle_config,
}


# ── MCP JSON-RPC Protocol ──────────────────────────────────────────────────

def handle_jsonrpc(request: dict) -> dict:
    """Handle a single JSON-RPC request."""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return _response(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "engramkit", "version": "0.1.0"},
        })

    if method == "notifications/initialized":
        return None  # No response for notifications

    if method == "tools/list":
        return _response(req_id, {"tools": TOOLS})

    if method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})
        handler = HANDLERS.get(tool_name)
        if not handler:
            return _error(req_id, -32601, f"Unknown tool: {tool_name}")
        try:
            result = handler(tool_args)
            return _response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}],
            })
        except Exception as e:
            return _response(req_id, {
                "content": [{"type": "text", "text": f"Error: {e}"}],
                "isError": True,
            })

    return _error(req_id, -32601, f"Unknown method: {method}")


def _response(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def run_stdio():
    """Run MCP server on stdin/stdout (standard MCP transport)."""
    ENGRAMKIT_HOME.mkdir(parents=True, exist_ok=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        response = handle_jsonrpc(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_stdio()
