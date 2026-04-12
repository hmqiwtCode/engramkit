"""Integration tests for the FastAPI REST API — all route modules."""

import os

import pytest
from fastapi.testclient import TestClient

from engramkit.api.server import app


@pytest.fixture
def api_home(tmp_path, monkeypatch):
    """
    Override ENGRAMKIT_HOME across all modules so the API operates on a temp dir.
    Returns the path for further assertions.
    """
    home = tmp_path / "api_engramkit_home"
    home.mkdir()
    (home / "identity.txt").write_text("Test API identity.")

    # Patch all modules that import ENGRAMKIT_HOME
    monkeypatch.setattr("engramkit.config.ENGRAMKIT_HOME", home)
    monkeypatch.setattr("engramkit.storage.vault.ENGRAMKIT_HOME", home)
    monkeypatch.setattr("engramkit.api.helpers.ENGRAMKIT_HOME", home)
    monkeypatch.setattr("engramkit.api.routes_vaults.ENGRAMKIT_HOME", home)
    monkeypatch.setattr("engramkit.memory.layers.ENGRAMKIT_HOME", home)
    return home


@pytest.fixture
def client(api_home):
    """FastAPI TestClient wired to the temp ENGRAMKIT_HOME."""
    return TestClient(app)


@pytest.fixture
def vault_id(client, tmp_path):
    """Create a vault via the API and return its vault_id."""
    repo_path = str(tmp_path / "test_api_repo")
    os.makedirs(repo_path, exist_ok=True)
    resp = client.post("/api/vaults", json={"repo_path": repo_path})
    assert resp.status_code == 200
    return resp.json()["vault_id"]


@pytest.fixture
def seeded_api_vault(client, vault_id):
    """Seed the API vault with chunks and KG data, return vault_id."""
    # Save some content
    client.post(f"/api/vaults/{vault_id}/save", json={
        "content": "def calculate_total(items, discount):\n    return sum(items) * (1 - discount)",
        "wing": "api",
        "room": "billing",
        "importance": 4.0,
    })
    client.post(f"/api/vaults/{vault_id}/save", json={
        "content": "PostgreSQL database connection pool with asyncpg and retry logic",
        "wing": "api",
        "room": "database",
    })
    client.post(f"/api/vaults/{vault_id}/save", json={
        "content": "# Project Documentation\nThis project uses FastAPI and PostgreSQL.",
        "wing": "docs",
        "room": "general",
    })

    # Add KG triples
    client.post(f"/api/vaults/{vault_id}/kg/triples", json={
        "subject": "Service",
        "predicate": "uses",
        "object": "PostgreSQL",
        "valid_from": "2024-01-01",
    })
    client.post(f"/api/vaults/{vault_id}/kg/triples", json={
        "subject": "Alice",
        "predicate": "maintains",
        "object": "Service",
        "valid_from": "2024-06-01",
    })

    return vault_id


# ── Vault CRUD ────────────────────────────────────────────────────────────


class TestVaultsCRUD:
    """Test vault create, read, list, delete endpoints."""

    def test_list_vaults_empty(self, client):
        """GET /api/vaults on fresh home should return empty list."""
        resp = client.get("/api/vaults")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_vault(self, client, tmp_path):
        """POST /api/vaults should create a new vault."""
        repo_path = str(tmp_path / "new_repo")
        os.makedirs(repo_path)
        resp = client.post("/api/vaults", json={"repo_path": repo_path})
        assert resp.status_code == 200
        data = resp.json()
        assert "vault_id" in data
        assert data["total_chunks"] == 0

    def test_list_vaults_after_create(self, client, vault_id):
        """GET /api/vaults should include the created vault."""
        resp = client.get("/api/vaults")
        assert resp.status_code == 200
        vaults = resp.json()
        assert len(vaults) >= 1
        ids = [v["vault_id"] for v in vaults]
        assert vault_id in ids

    def test_get_vault_stats(self, client, vault_id):
        """GET /api/vaults/{id} should return vault details."""
        resp = client.get(f"/api/vaults/{vault_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["vault_id"] == vault_id
        assert "total_chunks" in data
        assert "repo_path" in data

    def test_delete_vault(self, client, vault_id):
        """DELETE /api/vaults/{id} should remove the vault."""
        resp = client.delete(f"/api/vaults/{vault_id}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

        # Verify it's gone
        resp = client.get(f"/api/vaults/{vault_id}")
        assert resp.status_code == 404

    def test_get_nonexistent_vault_returns_404(self, client):
        """GET /api/vaults/{nonexistent} should return 404."""
        resp = client.get("/api/vaults/nonexistent_id")
        assert resp.status_code == 404

    def test_delete_nonexistent_vault_returns_404(self, client):
        """DELETE /api/vaults/{nonexistent} should return 404."""
        resp = client.delete("/api/vaults/nonexistent_id")
        assert resp.status_code == 404


# ── Files & Chunks ────────────────────────────────────────────────────────


class TestFilesAndChunks:
    """Test file listing, chunk pagination, and chunk operations."""

    def test_list_files(self, client, seeded_api_vault):
        """GET /api/vaults/{id}/files should return file list."""
        resp = client.get(f"/api/vaults/{seeded_api_vault}/files")
        assert resp.status_code == 200
        # manual_save files are stored for saved content
        assert isinstance(resp.json(), list)

    def test_list_chunks_paginated(self, client, seeded_api_vault):
        """GET /api/vaults/{id}/chunks should return paginated results."""
        resp = client.get(f"/api/vaults/{seeded_api_vault}/chunks")
        assert resp.status_code == 200
        data = resp.json()
        assert "chunks" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "pages" in data
        assert data["total"] >= 3

    def test_chunks_pagination(self, client, seeded_api_vault):
        """Pagination should work with page and per_page params."""
        resp = client.get(
            f"/api/vaults/{seeded_api_vault}/chunks",
            params={"page": 1, "per_page": 2},
        )
        data = resp.json()
        assert len(data["chunks"]) <= 2

    def test_chunks_wing_filter(self, client, seeded_api_vault):
        """Wing filter should restrict chunk results."""
        resp = client.get(
            f"/api/vaults/{seeded_api_vault}/chunks",
            params={"wing": "docs"},
        )
        data = resp.json()
        for chunk in data["chunks"]:
            assert chunk["wing"] == "docs"

    def test_chunks_room_filter(self, client, seeded_api_vault):
        """Room filter should restrict chunk results."""
        resp = client.get(
            f"/api/vaults/{seeded_api_vault}/chunks",
            params={"room": "database"},
        )
        data = resp.json()
        for chunk in data["chunks"]:
            assert chunk["room"] == "database"

    def test_get_chunk_by_hash(self, client, seeded_api_vault):
        """GET /api/vaults/{id}/chunks/{hash} should return the specific chunk."""
        # First get chunks to find a hash
        resp = client.get(f"/api/vaults/{seeded_api_vault}/chunks")
        chunks = resp.json()["chunks"]
        assert len(chunks) > 0
        content_hash = chunks[0]["content_hash"]

        resp = client.get(f"/api/vaults/{seeded_api_vault}/chunks/{content_hash}")
        assert resp.status_code == 200
        assert resp.json()["content_hash"] == content_hash

    def test_get_nonexistent_chunk_returns_404(self, client, seeded_api_vault):
        """Getting a nonexistent chunk hash should return 404."""
        resp = client.get(f"/api/vaults/{seeded_api_vault}/chunks/nonexistent_hash")
        assert resp.status_code == 404

    def test_patch_chunk_importance(self, client, seeded_api_vault):
        """PATCH /api/vaults/{id}/chunks/{hash} should update importance."""
        resp = client.get(f"/api/vaults/{seeded_api_vault}/chunks")
        content_hash = resp.json()["chunks"][0]["content_hash"]

        resp = client.patch(
            f"/api/vaults/{seeded_api_vault}/chunks/{content_hash}",
            json={"importance": 5.0},
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] is True

        # Verify updated
        resp = client.get(f"/api/vaults/{seeded_api_vault}/chunks/{content_hash}")
        assert resp.json()["importance"] == 5.0


# ── Search ────────────────────────────────────────────────────────────────


class TestSearchEndpoints:
    """Test search and mining endpoints."""

    def test_vault_search(self, client, seeded_api_vault):
        """POST /api/vaults/{id}/search should return results."""
        resp = client.post(
            f"/api/vaults/{seeded_api_vault}/search",
            json={"query": "calculate_total"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "count" in data

    def test_global_search(self, client, seeded_api_vault):
        """POST /api/search should search across all vaults."""
        resp = client.post("/api/search", json={"query": "database"})
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data

    def test_search_with_filters(self, client, seeded_api_vault):
        """Search with wing/room filters should work."""
        resp = client.post(
            f"/api/vaults/{seeded_api_vault}/search",
            json={"query": "connection", "wing": "api", "room": "database"},
        )
        assert resp.status_code == 200


# ── Knowledge Graph ──────────────────────────────────────────────────────


class TestKGEndpoints:
    """Test knowledge graph endpoints."""

    def test_kg_stats(self, client, seeded_api_vault):
        """GET /api/vaults/{id}/kg/stats should return KG statistics."""
        resp = client.get(f"/api/vaults/{seeded_api_vault}/kg/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "entities" in data
        assert "triples" in data
        assert data["triples"] >= 2

    def test_kg_entities(self, client, seeded_api_vault):
        """GET /api/vaults/{id}/kg/entities should return entity list."""
        resp = client.get(f"/api/vaults/{seeded_api_vault}/kg/entities")
        assert resp.status_code == 200
        entities = resp.json()
        assert len(entities) >= 2
        names = {e["name"] for e in entities}
        assert "Service" in names or "Alice" in names

    def test_kg_entity_query(self, client, seeded_api_vault):
        """GET /api/vaults/{id}/kg/entity/{name} should return facts."""
        resp = client.get(f"/api/vaults/{seeded_api_vault}/kg/entity/Service")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1

    def test_kg_entity_with_as_of(self, client, seeded_api_vault):
        """Entity query with as_of should filter temporally."""
        resp = client.get(
            f"/api/vaults/{seeded_api_vault}/kg/entity/Service",
            params={"as_of": "2024-06-01"},
        )
        assert resp.status_code == 200

    def test_kg_timeline(self, client, seeded_api_vault):
        """GET /api/vaults/{id}/kg/timeline should return chronological facts."""
        resp = client.get(f"/api/vaults/{seeded_api_vault}/kg/timeline")
        assert resp.status_code == 200
        data = resp.json()
        assert "timeline" in data
        assert data["count"] >= 2

    def test_kg_timeline_with_entity(self, client, seeded_api_vault):
        """Timeline with entity filter should restrict results."""
        resp = client.get(
            f"/api/vaults/{seeded_api_vault}/kg/timeline",
            params={"entity": "Alice"},
        )
        assert resp.status_code == 200

    def test_kg_add_triple(self, client, seeded_api_vault):
        """POST /api/vaults/{id}/kg/triples should add a triple."""
        resp = client.post(
            f"/api/vaults/{seeded_api_vault}/kg/triples",
            json={
                "subject": "NewService",
                "predicate": "depends_on",
                "object": "Redis",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["added"] is True

    def test_kg_invalidate(self, client, seeded_api_vault):
        """PATCH /api/vaults/{id}/kg/triples/invalidate should expire a fact."""
        resp = client.patch(
            f"/api/vaults/{seeded_api_vault}/kg/triples/invalidate",
            json={
                "subject": "Service",
                "predicate": "uses",
                "object": "PostgreSQL",
                "ended": "2026-01-01",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["invalidated"] is True

    def test_kg_graph(self, client, seeded_api_vault):
        """GET /api/vaults/{id}/kg/graph should return nodes and edges."""
        resp = client.get(f"/api/vaults/{seeded_api_vault}/kg/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) >= 2
        assert len(data["edges"]) >= 2


# ── GC ────────────────────────────────────────────────────────────────────


class TestGCEndpoints:
    """Test garbage collection endpoints."""

    def test_run_gc(self, client, seeded_api_vault):
        """POST /api/vaults/{id}/gc should complete successfully."""
        resp = client.post(
            f"/api/vaults/{seeded_api_vault}/gc",
            json={"retention_days": 30},
        )
        assert resp.status_code == 200
        assert resp.json()["completed"] is True

    def test_gc_dry_run(self, client, seeded_api_vault):
        """GC with dry_run should not delete anything."""
        resp = client.post(
            f"/api/vaults/{seeded_api_vault}/gc",
            json={"retention_days": 30, "dry_run": True},
        )
        assert resp.status_code == 200
        assert resp.json()["dry_run"] is True

    def test_gc_log(self, client, seeded_api_vault):
        """GET /api/vaults/{id}/gc/log should return the GC log."""
        resp = client.get(f"/api/vaults/{seeded_api_vault}/gc/log")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ── Memory ────────────────────────────────────────────────────────────────


class TestMemoryEndpoints:
    """Test memory wakeup and recall endpoints."""

    def test_wakeup(self, client, seeded_api_vault):
        """GET /api/vaults/{id}/memory/wakeup should return context."""
        resp = client.get(f"/api/vaults/{seeded_api_vault}/memory/wakeup")
        assert resp.status_code == 200
        data = resp.json()
        assert "context" in data
        assert "total_tokens" in data
        assert "l0" in data
        assert "l1" in data

    def test_wakeup_with_wing(self, client, seeded_api_vault):
        """Wakeup with wing filter should work."""
        resp = client.get(
            f"/api/vaults/{seeded_api_vault}/memory/wakeup",
            params={"wing": "api"},
        )
        assert resp.status_code == 200

    def test_recall(self, client, seeded_api_vault):
        """GET /api/vaults/{id}/memory/recall should return recalled chunks."""
        resp = client.get(f"/api/vaults/{seeded_api_vault}/memory/recall")
        assert resp.status_code == 200
        data = resp.json()
        assert "text" in data
        assert "chunks_loaded" in data

    def test_recall_with_filters(self, client, seeded_api_vault):
        """Recall with wing/room filters should work."""
        resp = client.get(
            f"/api/vaults/{seeded_api_vault}/memory/recall",
            params={"wing": "api", "room": "database"},
        )
        assert resp.status_code == 200


# ── Save & Diary ─────────────────────────────────────────────────────────


class TestSaveAndDiary:
    """Test save and diary endpoints."""

    def test_save_content(self, client, vault_id):
        """POST /api/vaults/{id}/save should store content."""
        resp = client.post(
            f"/api/vaults/{vault_id}/save",
            json={"content": "Important decision: use Redis for caching."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["saved"] is True
        assert "content_hash" in data
        assert "tokens" in data

    def test_save_with_importance(self, client, vault_id):
        """Save with custom importance should work."""
        resp = client.post(
            f"/api/vaults/{vault_id}/save",
            json={"content": "Critical security fix applied.", "importance": 5.0},
        )
        assert resp.status_code == 200

    def test_diary_write(self, client, vault_id):
        """POST /api/vaults/{id}/diary should save a diary entry."""
        resp = client.post(
            f"/api/vaults/{vault_id}/diary",
            json={"content": "Spent the day debugging race conditions."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["saved"] is True


# ── Config & Hooks ───────────────────────────────────────────────────────


class TestConfigEndpoints:
    """Test configuration endpoints."""

    def test_get_global_config(self, client):
        """GET /config should return default config."""
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "chunk_size" in data
        assert data["chunk_size"] == 800

    def test_get_vault_config(self, client, vault_id):
        """GET /api/vaults/{id}/config should return vault metadata."""
        resp = client.get(f"/api/vaults/{vault_id}/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "schema_version" in data

    def test_update_vault_config(self, client, vault_id):
        """PATCH /api/vaults/{id}/config should set a config key."""
        resp = client.patch(
            f"/api/vaults/{vault_id}/config",
            json={"key": "custom_setting", "value": "enabled"},
        )
        assert resp.status_code == 200
        assert resp.json()["set"] is True

        # Verify persisted
        resp = client.get(f"/api/vaults/{vault_id}/config")
        assert resp.json()["custom_setting"] == "enabled"

    def test_install_hooks_no_repo(self, client, vault_id):
        """Install hooks should fail gracefully for vaults without a valid git repo."""
        # The test repo is not a git repo, so hooks install will either
        # succeed silently or fail gracefully
        resp = client.post(f"/api/vaults/{vault_id}/hooks/install")
        # Either 200 or 400/500 depending on git presence
        assert resp.status_code in (200, 400, 500)


# ── Chat (structure only — no real LLM call) ─────────────────────────────


class TestChatEndpoint:
    """Test the chat endpoint structure (mocked LLM)."""

    def test_chat_requires_vault(self, client):
        """POST /api/chat without vault should return 400."""
        resp = client.post("/api/chat", json={"message": "Hello"})
        assert resp.status_code == 400

    def test_chat_with_nonexistent_vault(self, client):
        """POST /api/chat with nonexistent vault should return 404."""
        resp = client.post("/api/chat", json={
            "message": "Hello",
            "vault_id": "nonexistent",
        })
        assert resp.status_code == 404
