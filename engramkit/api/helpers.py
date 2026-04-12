"""Shared helpers and request models for API routes."""

from typing import Optional
from fastapi import HTTPException
from pydantic import BaseModel

from engramkit.config import ENGRAMKIT_HOME
from engramkit.storage.vault import Vault
from engramkit.graph.knowledge_graph import KnowledgeGraph


def get_vault_by_id(vault_id: str) -> Vault:
    vault_path = ENGRAMKIT_HOME / "vaults" / vault_id
    if not vault_path.exists():
        raise HTTPException(404, f"Vault {vault_id} not found")
    vault = Vault(vault_path)
    vault.open()
    return vault


def get_kg(vault: Vault) -> KnowledgeGraph:
    return KnowledgeGraph(str(vault.vault_path / "knowledge_graph.sqlite3"))


# ── Request Models ────────────────────────────────────────────────────────

class CreateVaultRequest(BaseModel):
    repo_path: str

class SearchRequest(BaseModel):
    query: str
    wing: Optional[str] = None
    room: Optional[str] = None
    n_results: int = 5

class MineRequest(BaseModel):
    wing: Optional[str] = None
    room: str = "general"
    full: bool = False
    dry_run: bool = False

class GCRequest(BaseModel):
    retention_days: int = 30
    dry_run: bool = False

class SaveRequest(BaseModel):
    content: str
    wing: Optional[str] = None
    room: str = "general"
    importance: float = 3.0

class DiaryRequest(BaseModel):
    content: str
    wing: str = "diary"

class AddTripleRequest(BaseModel):
    subject: str
    predicate: str
    object: str
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    confidence: float = 1.0

class InvalidateRequest(BaseModel):
    subject: str
    predicate: str
    object: str
    ended: Optional[str] = None

class UpdateChunkRequest(BaseModel):
    importance: Optional[float] = None

class ConfigUpdateRequest(BaseModel):
    key: str
    value: str

class ChatRequest(BaseModel):
    message: str
    mode: str = "rag"             # "rag" = EngramKit search + Claude, "direct" = Claude only (no RAG)
    vault_id: Optional[str] = None
    vault_ids: Optional[list] = None
    n_context: int = 10
    model: str = "claude-sonnet-4-20250514"
    history: list = []
    pinned_chunks: list = []
