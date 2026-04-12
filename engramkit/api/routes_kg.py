"""Knowledge graph endpoints."""

from typing import Optional
from fastapi import APIRouter

from engramkit.api.helpers import get_vault_by_id, get_kg, AddTripleRequest, InvalidateRequest
from engramkit.storage.gc import run_gc as _run_gc
from engramkit.api.helpers import GCRequest

router = APIRouter(prefix="/api", tags=["knowledge-graph"])


@router.get("/vaults/{vault_id}/kg/stats")
def kg_stats(vault_id: str):
    vault = get_vault_by_id(vault_id)
    try:
        kg = get_kg(vault); s = kg.stats(); kg.close(); return s
    finally:
        vault.close()


@router.get("/vaults/{vault_id}/kg/entities")
def kg_entities(vault_id: str):
    vault = get_vault_by_id(vault_id)
    try:
        kg = get_kg(vault)
        rows = kg.conn.execute("SELECT * FROM entities ORDER BY name").fetchall()
        kg.close(); return [dict(r) for r in rows]
    finally:
        vault.close()


@router.get("/vaults/{vault_id}/kg/entity/{name}")
def kg_entity(vault_id: str, name: str, as_of: Optional[str] = None, direction: str = "both"):
    vault = get_vault_by_id(vault_id)
    try:
        kg = get_kg(vault)
        facts = kg.query_entity(name, as_of=as_of, direction=direction)
        kg.close(); return {"entity": name, "facts": facts, "count": len(facts)}
    finally:
        vault.close()


@router.get("/vaults/{vault_id}/kg/timeline")
def kg_timeline(vault_id: str, entity: Optional[str] = None):
    vault = get_vault_by_id(vault_id)
    try:
        kg = get_kg(vault); t = kg.timeline(entity); kg.close()
        return {"timeline": t, "count": len(t)}
    finally:
        vault.close()


@router.post("/vaults/{vault_id}/kg/triples")
def kg_add(vault_id: str, req: AddTripleRequest):
    vault = get_vault_by_id(vault_id)
    try:
        kg = get_kg(vault)
        tid = kg.add_triple(req.subject, req.predicate, req.object,
                            valid_from=req.valid_from, valid_to=req.valid_to, confidence=req.confidence)
        kg.close(); return {"added": True, "triple_id": tid}
    finally:
        vault.close()


@router.patch("/vaults/{vault_id}/kg/triples/invalidate")
def kg_invalidate(vault_id: str, req: InvalidateRequest):
    vault = get_vault_by_id(vault_id)
    try:
        kg = get_kg(vault)
        kg.invalidate(req.subject, req.predicate, req.object, ended=req.ended)
        kg.close(); return {"invalidated": True}
    finally:
        vault.close()


@router.get("/vaults/{vault_id}/kg/graph")
def kg_graph(vault_id: str):
    vault = get_vault_by_id(vault_id)
    try:
        kg = get_kg(vault)
        entities = kg.conn.execute("SELECT id, name, type FROM entities").fetchall()
        triples = kg.conn.execute(
            """SELECT s.name as source, t.predicate, o.name as target, t.valid_to
               FROM triples t JOIN entities s ON t.subject=s.id JOIN entities o ON t.object=o.id"""
        ).fetchall()
        kg.close()
        return {
            "nodes": [{"id": r["id"], "name": r["name"], "type": r["type"]} for r in entities],
            "edges": [{"source": r["source"], "target": r["target"], "predicate": r["predicate"],
                       "current": r["valid_to"] is None} for r in triples],
        }
    finally:
        vault.close()


# ── GC ────────────────────────────────────────────────────────────────────

@router.post("/vaults/{vault_id}/gc")
def gc_vault(vault_id: str, req: GCRequest):
    vault = get_vault_by_id(vault_id)
    try:
        _run_gc(vault, dry_run=req.dry_run, retention_days=req.retention_days)
        return {"completed": True, "dry_run": req.dry_run}
    finally:
        vault.close()


@router.get("/vaults/{vault_id}/gc/log")
def gc_log(vault_id: str, limit: int = 100):
    vault = get_vault_by_id(vault_id)
    try:
        rows = vault.conn.execute("SELECT * FROM gc_log ORDER BY performed_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        vault.close()
