"""Search and mining endpoints."""

from fastapi import APIRouter, HTTPException

from engramkit.storage.vault import VaultManager
from engramkit.search.hybrid import hybrid_search
from engramkit.api.helpers import get_vault_by_id, SearchRequest, MineRequest

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search")
def global_search(req: SearchRequest):
    all_results = []
    for vault_info in VaultManager.list_vaults():
        vault = get_vault_by_id(vault_info["vault_id"])
        try:
            results = hybrid_search(req.query, vault, req.n_results, req.wing, req.room)
            for r in results:
                r["vault_id"] = vault_info["vault_id"]
                r["repo_path"] = vault_info["repo_path"]
            all_results.extend(results)
        finally:
            vault.close()
    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return {"query": req.query, "results": all_results[:req.n_results], "count": len(all_results)}


@router.post("/vaults/{vault_id}/search")
def vault_search(vault_id: str, req: SearchRequest):
    vault = get_vault_by_id(vault_id)
    try:
        results = hybrid_search(req.query, vault, req.n_results, req.wing, req.room)
        return {"query": req.query, "results": results, "count": len(results)}
    finally:
        vault.close()


@router.post("/vaults/{vault_id}/mine")
def mine_vault(vault_id: str, req: MineRequest):
    from engramkit.ingest.pipeline import mine
    vault = get_vault_by_id(vault_id)
    repo_path = vault.get_meta("repo_path")
    if not repo_path:
        vault.close()
        raise HTTPException(400, "No repo_path stored for this vault")
    try:
        return mine(repo_path, vault, wing=req.wing, room=req.room, full=req.full, dry_run=req.dry_run)
    finally:
        vault.close()
