"""Vault CRUD + files + chunks endpoints."""

import shutil
from typing import Optional
from fastapi import APIRouter, HTTPException

from engramkit.config import ENGRAMKIT_HOME
from engramkit.storage.vault import VaultManager
from engramkit.api.helpers import get_vault_by_id, CreateVaultRequest, UpdateChunkRequest

router = APIRouter(prefix="/api", tags=["vaults"])


@router.get("/vaults")
def list_vaults():
    return VaultManager.list_vaults()


@router.post("/vaults")
def create_vault(req: CreateVaultRequest):
    vault = VaultManager.get_vault(req.repo_path)
    vault_id = VaultManager.vault_id(req.repo_path)
    stats = vault.stats()
    vault.close()
    return {"vault_id": vault_id, "repo_path": req.repo_path, **stats}


@router.get("/vaults/{vault_id}")
def get_vault(vault_id: str):
    vault = get_vault_by_id(vault_id)
    try:
        stats = vault.stats()
        meta = {
            "repo_path": vault.get_meta("repo_path", "unknown"),
            "wing": vault.get_meta("wing"),
            "last_commit": vault.get_meta("last_commit"),
            "last_branch": vault.get_meta("last_branch"),
        }
        return {"vault_id": vault_id, **meta, **stats}
    finally:
        vault.close()


@router.delete("/vaults/{vault_id}")
def delete_vault(vault_id: str):
    vault_path = ENGRAMKIT_HOME / "vaults" / vault_id
    if not vault_path.exists():
        raise HTTPException(404, "Vault not found")
    shutil.rmtree(vault_path)
    return {"deleted": True}


# ── Files & Chunks ────────────────────────────────────────────────────────

@router.get("/vaults/{vault_id}/files")
def list_files(vault_id: str):
    vault = get_vault_by_id(vault_id)
    try:
        rows = vault.conn.execute("SELECT * FROM files WHERE is_deleted = 0 ORDER BY file_path").fetchall()
        return [dict(r) for r in rows]
    finally:
        vault.close()


@router.get("/vaults/{vault_id}/chunks")
def list_chunks(
    vault_id: str, wing: Optional[str] = None, room: Optional[str] = None,
    is_stale: Optional[bool] = None, is_secret: Optional[bool] = None,
    page: int = 1, per_page: int = 50,
):
    vault = get_vault_by_id(vault_id)
    try:
        sql, params = "SELECT * FROM chunks WHERE 1=1", []
        if wing: sql += " AND wing = ?"; params.append(wing)
        if room: sql += " AND room = ?"; params.append(room)
        if is_stale is not None: sql += " AND is_stale = ?"; params.append(1 if is_stale else 0)
        if is_secret is not None: sql += " AND is_secret = ?"; params.append(1 if is_secret else 0)

        total = vault.conn.execute(sql.replace("SELECT *", "SELECT COUNT(*) as c"), params).fetchone()["c"]
        sql += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        rows = vault.conn.execute(sql, params).fetchall()

        return {"chunks": [dict(r) for r in rows], "total": total, "page": page, "per_page": per_page,
                "pages": (total + per_page - 1) // per_page}
    finally:
        vault.close()


@router.get("/vaults/{vault_id}/chunks/{content_hash}")
def get_chunk(vault_id: str, content_hash: str):
    vault = get_vault_by_id(vault_id)
    try:
        row = vault.conn.execute("SELECT * FROM chunks WHERE content_hash = ?", (content_hash,)).fetchone()
        if not row: raise HTTPException(404, "Chunk not found")
        return dict(row)
    finally:
        vault.close()


@router.patch("/vaults/{vault_id}/chunks/{content_hash}")
def update_chunk(vault_id: str, content_hash: str, req: UpdateChunkRequest):
    vault = get_vault_by_id(vault_id)
    try:
        if req.importance is not None:
            vault.conn.execute("UPDATE chunks SET importance = ? WHERE content_hash = ?", (req.importance, content_hash))
            vault.conn.commit()
        return {"updated": True}
    finally:
        vault.close()
