"""Shared fixtures for EngramKit test suite."""


import pytest

from engramkit.storage.vault import Vault
from engramkit.storage.schema import init_db
from engramkit.graph.knowledge_graph import KnowledgeGraph


# ---------------------------------------------------------------------------
# Temporary vault fixture (SQLite + ChromaDB)
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_vault(tmp_path):
    """Create a fresh, empty vault in a temp directory and return it open."""
    vault = Vault(tmp_path / "test_vault")
    vault.open()
    yield vault
    vault.close()


@pytest.fixture
def seeded_vault(tmp_path):
    """Vault pre-loaded with representative chunks for search/memory tests."""
    vault = Vault(tmp_path / "seeded_vault")
    vault.open()

    chunks = [
        {
            "content_hash": "h_billing",
            "content": "def calculate_total(items, discount):\n    validate(items)\n    return sum(items) * (1 - discount)",
            "file_path": "billing_service.py",
            "file_hash": "f1",
            "wing": "api",
            "room": "billing",
            "generation": 1,
        },
        {
            "content_hash": "h_db",
            "content": "PostgreSQL database connection pool setup using asyncpg with retry logic",
            "file_path": "db.py",
            "file_hash": "f2",
            "wing": "api",
            "room": "database",
            "generation": 1,
        },
        {
            "content_hash": "h_webhook",
            "content": "async def handle_webhook(request):\n    validate(request)\n    process(request.body)",
            "file_path": "webhook.py",
            "file_hash": "f3",
            "wing": "api",
            "room": "webhooks",
            "generation": 1,
        },
        {
            "content_hash": "h_secret",
            "content": "SECRET_KEY=super_secret_password_12345678",
            "file_path": ".env",
            "file_hash": "f4",
            "wing": "api",
            "room": "general",
            "generation": 1,
            "is_secret": 1,
        },
        {
            "content_hash": "h_readme",
            "content": "# Acme Corp Billing System\nThis service handles processing invoices via the Acme Corp API.",
            "file_path": "README.md",
            "file_hash": "f5",
            "wing": "docs",
            "room": "general",
            "generation": 1,
        },
    ]
    vault.batch_upsert_chunks(chunks)

    # Track files
    vault.upsert_file("billing_service.py", "f1", 1)
    vault.upsert_file("db.py", "f2", 1)
    vault.upsert_file("webhook.py", "f3", 1)
    vault.upsert_file("README.md", "f5", 1)

    yield vault
    vault.close()


# ---------------------------------------------------------------------------
# SQLite-only fixture (no ChromaDB) for fast schema/FTS tests
# ---------------------------------------------------------------------------

@pytest.fixture
def db_conn(tmp_path):
    """Raw SQLite connection initialized with EngramKit schema."""
    db_path = str(tmp_path / "test.sqlite3")
    conn = init_db(db_path)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Knowledge graph fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def kg(tmp_path):
    """Fresh knowledge graph instance."""
    g = KnowledgeGraph(str(tmp_path / "test_kg.sqlite3"))
    yield g
    g.close()


@pytest.fixture
def seeded_kg(tmp_path):
    """Knowledge graph pre-loaded with sample triples."""
    g = KnowledgeGraph(str(tmp_path / "seeded_kg.sqlite3"))
    g.add_triple("Alice", "works_at", "Acme Corp", valid_from="2024-01-01")
    g.add_triple("Bob", "works_at", "Acme Corp", valid_from="2024-03-01")
    g.add_triple("Alice", "manages", "Bob", valid_from="2024-06-01")
    g.add_triple("Acme Corp", "uses", "PostgreSQL", valid_from="2023-01-01")
    yield g
    g.close()


# ---------------------------------------------------------------------------
# Project directory fixture for pipeline/mine tests
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_project(tmp_path):
    """Create a minimal project directory with files for mining tests."""
    proj = tmp_path / "sample_project"
    proj.mkdir()

    # Python files
    (proj / "main.py").write_text(
        "def main():\n    print('hello world')\n\nif __name__ == '__main__':\n    main()\n"
    )
    (proj / "utils.py").write_text(
        "def helper_func(x):\n    return x * 2\n\ndef another_helper(y):\n    return y + 1\n"
    )

    # Subdirectory
    sub = proj / "lib"
    sub.mkdir()
    (sub / "core.py").write_text(
        "class Engine:\n    def run(self):\n        pass\n\n    def stop(self):\n        pass\n"
    )

    # Non-readable file
    (proj / "image.png").write_bytes(b"\x89PNG fake binary data")

    # Secret file
    (proj / ".env").write_text("DATABASE_URL=postgres://user:pass@localhost/db\n")

    # Gitignore
    (proj / ".gitignore").write_text("*.pyc\n__pycache__/\n.env\nbuild/\n")

    # Small file (should be skipped by min_size)
    (proj / "tiny.py").write_text("x=1")

    return proj


# ---------------------------------------------------------------------------
# ENGRAMKIT_HOME override for API tests
# ---------------------------------------------------------------------------

@pytest.fixture
def engramkit_home(tmp_path, monkeypatch):
    """Override ENGRAMKIT_HOME to a temp dir so API tests don't pollute real data."""
    home = tmp_path / "engramkit_home"
    home.mkdir()
    monkeypatch.setattr("engramkit.config.ENGRAMKIT_HOME", home)
    monkeypatch.setattr("engramkit.storage.vault.ENGRAMKIT_HOME", home)
    monkeypatch.setattr("engramkit.api.helpers.ENGRAMKIT_HOME", home)
    monkeypatch.setattr("engramkit.api.routes_vaults.ENGRAMKIT_HOME", home)
    monkeypatch.setattr("engramkit.api.routes_memory.ENGRAMKIT_HOME", home)
    monkeypatch.setattr("engramkit.memory.layers.ENGRAMKIT_HOME", home)
    return home
