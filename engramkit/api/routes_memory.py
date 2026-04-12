"""Memory, save, diary, config, and hooks endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException

from engramkit.memory.layers import MemoryStack
from engramkit.memory.token_budget import TokenBudget, count_tokens
from engramkit.ingest.chunker import content_hash
from engramkit.api.helpers import get_vault_by_id, SaveRequest, DiaryRequest, ConfigUpdateRequest

router = APIRouter(prefix="/api", tags=["memory"])


@router.get("/vaults/{vault_id}/memory/wakeup")
def memory_wakeup(vault_id: str, wing: Optional[str] = None, l1_tokens: int = 1000):
    vault = get_vault_by_id(vault_id)
    try:
        stack = MemoryStack(vault, TokenBudget(l1_max=l1_tokens))
        result = stack.wake_up(wing=wing)
        return {
            "context": result["text"], "total_tokens": result["total_tokens"],
            "l0": {"tokens": result["l0_report"].tokens_used, "budget": result["l0_report"].tokens_budget},
            "l1": {"tokens": result["l1_report"].tokens_used, "budget": result["l1_report"].tokens_budget,
                    "loaded": result["l1_report"].chunks_loaded, "deduped": result["l1_report"].chunks_skipped_dedup},
        }
    finally:
        vault.close()


@router.get("/vaults/{vault_id}/memory/recall")
def memory_recall(vault_id: str, wing: Optional[str] = None, room: Optional[str] = None, n_results: int = 10):
    vault = get_vault_by_id(vault_id)
    try:
        result = MemoryStack(vault).recall(wing=wing, room=room, n_results=n_results)
        return {"text": result["text"], "tokens": result["report"].tokens_used, "chunks_loaded": result["report"].chunks_loaded}
    finally:
        vault.close()


# ── Save & Diary ──────────────────────────────────────────────────────────

@router.post("/vaults/{vault_id}/save")
def save_content(vault_id: str, req: SaveRequest):
    vault = get_vault_by_id(vault_id)
    try:
        chash = content_hash(req.content)
        wing = req.wing or vault.get_meta("wing") or "default"
        vault.batch_upsert_chunks([{
            "content_hash": chash, "content": req.content, "file_path": "manual_save", "file_hash": chash,
            "wing": wing, "room": req.room, "generation": vault.current_generation(),
            "importance": req.importance, "is_secret": 0,
        }])
        return {"saved": True, "content_hash": chash, "tokens": count_tokens(req.content)}
    finally:
        vault.close()


@router.post("/vaults/{vault_id}/diary")
def write_diary(vault_id: str, req: DiaryRequest):
    from datetime import datetime
    vault = get_vault_by_id(vault_id)
    try:
        entry = f"[{datetime.now().isoformat()}] {req.content}"
        chash = content_hash(entry)
        vault.batch_upsert_chunks([{
            "content_hash": chash, "content": entry, "file_path": "diary", "file_hash": chash,
            "wing": f"agent_{req.wing}", "room": "diary", "generation": vault.current_generation(),
            "importance": 2.0, "is_secret": 0,
        }])
        return {"saved": True, "content_hash": chash}
    finally:
        vault.close()


# ── Config & Hooks ────────────────────────────────────────────────────────

@router.get("/config")
def get_config():
    from engramkit.config import DEFAULTS
    return DEFAULTS


@router.get("/vaults/{vault_id}/config")
def get_vault_config(vault_id: str):
    vault = get_vault_by_id(vault_id)
    try:
        rows = vault.conn.execute("SELECT key, value FROM vault_meta").fetchall()
        return {r["key"]: r["value"] for r in rows}
    finally:
        vault.close()


@router.patch("/vaults/{vault_id}/config")
def update_vault_config(vault_id: str, req: ConfigUpdateRequest):
    vault = get_vault_by_id(vault_id)
    try:
        vault.set_meta(req.key, req.value)
        return {"set": True, "key": req.key, "value": req.value}
    finally:
        vault.close()


@router.post("/vaults/{vault_id}/hooks/install")
def install_hooks(vault_id: str):
    from engramkit.hooks.git_hooks import install_hooks as _install
    vault = get_vault_by_id(vault_id)
    try:
        repo_path = vault.get_meta("repo_path")
        if not repo_path: raise HTTPException(400, "No repo_path")
        _install(repo_path); return {"installed": True}
    finally:
        vault.close()
