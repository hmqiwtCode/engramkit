"""Tests for memory layers — L0 identity, L1 essential, L2 recall, L3 search."""


import pytest

from engramkit.storage.vault import Vault
from engramkit.memory.layers import MemoryStack
from engramkit.memory.token_budget import TokenBudget


@pytest.fixture
def memory_vault(tmp_path):
    """Vault with chunks for memory layer testing."""
    vault = Vault(tmp_path / "memory_vault")
    vault.open()

    chunks = [
        {
            "content_hash": "mem1",
            "content": "def authenticate(user, password):\n    return check_credentials(user, password)",
            "file_path": "auth.py",
            "file_hash": "f1",
            "wing": "api",
            "room": "auth",
            "generation": 1,
        },
        {
            "content_hash": "mem2",
            "content": "class DatabasePool:\n    def __init__(self):\n        self.pool = create_pool()",
            "file_path": "db.py",
            "file_hash": "f2",
            "wing": "api",
            "room": "database",
            "generation": 1,
        },
        {
            "content_hash": "mem3",
            "content": "def send_notification(user_id, message):\n    push_service.send(user_id, message)",
            "file_path": "notify.py",
            "file_hash": "f3",
            "wing": "api",
            "room": "notifications",
            "generation": 1,
        },
        {
            "content_hash": "mem_docs",
            "content": "# Project README\nThis project implements a notification service with auth and database layers.",
            "file_path": "README.md",
            "file_hash": "f4",
            "wing": "docs",
            "room": "general",
            "generation": 1,
        },
    ]
    vault.batch_upsert_chunks(chunks)
    yield vault
    vault.close()


@pytest.fixture
def identity_file(tmp_path, monkeypatch):
    """Create a temporary identity.txt and point ENGRAMKIT_HOME to it."""
    engramkit_home = tmp_path / "engramkit_home"
    engramkit_home.mkdir()
    identity = engramkit_home / "identity.txt"
    identity.write_text("You are Claude, an AI assistant helping with the Acme Corp codebase.")
    monkeypatch.setattr("engramkit.memory.layers.ENGRAMKIT_HOME", engramkit_home)
    return engramkit_home


@pytest.fixture
def no_identity(tmp_path, monkeypatch):
    """ENGRAMKIT_HOME without identity.txt."""
    engramkit_home = tmp_path / "engramkit_no_id"
    engramkit_home.mkdir()
    monkeypatch.setattr("engramkit.memory.layers.ENGRAMKIT_HOME", engramkit_home)
    return engramkit_home


class TestWakeUp:
    """Verify wake_up returns L0 + L1 context."""

    def test_returns_expected_structure(self, memory_vault, identity_file):
        """wake_up should return text, l0_report, l1_report, total_tokens."""
        stack = MemoryStack(memory_vault)
        result = stack.wake_up()
        assert "text" in result
        assert "l0_report" in result
        assert "l1_report" in result
        assert "total_tokens" in result
        assert isinstance(result["total_tokens"], int)

    def test_includes_identity(self, memory_vault, identity_file):
        """When identity.txt exists, L0 should load it."""
        stack = MemoryStack(memory_vault)
        result = stack.wake_up()
        assert "Identity" in result["text"]
        assert "Claude" in result["text"]

    def test_includes_recent_context(self, memory_vault, identity_file):
        """L1 should include recent chunks from the vault."""
        stack = MemoryStack(memory_vault, TokenBudget(l1_max=5000))
        result = stack.wake_up()
        assert "Recent Context" in result["text"]

    def test_total_tokens_positive(self, memory_vault, identity_file):
        """Total tokens should be > 0 when identity and chunks exist."""
        stack = MemoryStack(memory_vault)
        result = stack.wake_up()
        assert result["total_tokens"] > 0


class TestL0Identity:
    """Test L0 identity loading specifically."""

    def test_loads_identity_txt(self, memory_vault, identity_file):
        """L0 should read content from identity.txt."""
        stack = MemoryStack(memory_vault)
        text, report = stack._load_l0()
        assert "Claude" in text
        assert report.layer == "L0"
        assert report.tokens_used > 0

    def test_handles_missing_identity(self, memory_vault, no_identity):
        """Missing identity.txt should return empty text, not raise."""
        stack = MemoryStack(memory_vault)
        text, report = stack._load_l0()
        assert text == ""
        assert report.tokens_used == 0
        assert report.chunks_loaded == 0

    def test_respects_token_budget(self, memory_vault, tmp_path, monkeypatch):
        """L0 should truncate identity if it exceeds budget."""
        engramkit_home = tmp_path / "big_identity"
        engramkit_home.mkdir()
        # Write a large identity
        (engramkit_home / "identity.txt").write_text("word " * 500)
        monkeypatch.setattr("engramkit.memory.layers.ENGRAMKIT_HOME", engramkit_home)

        stack = MemoryStack(memory_vault, TokenBudget(l0_max=50))
        text, report = stack._load_l0()
        assert report.tokens_used <= 50 + 5  # Allow small margin for truncation


class TestL1Essential:
    """Test L1 essential context loading."""

    def test_loads_chunks(self, memory_vault, no_identity):
        """L1 should load chunks from the vault."""
        stack = MemoryStack(memory_vault, TokenBudget(l1_max=5000))
        text, report = stack._load_l1()
        assert report.chunks_loaded > 0
        assert report.layer == "L1"

    def test_respects_token_budget(self, memory_vault, no_identity):
        """L1 should not exceed the token budget."""
        # Very small budget — should only fit a couple of chunks
        stack = MemoryStack(memory_vault, TokenBudget(l1_max=50))
        text, report = stack._load_l1()
        assert report.tokens_used <= 50 + 20  # Allow margin for overhead

    def test_deduplicates(self, memory_vault, no_identity):
        """L1 should deduplicate near-identical chunks."""
        # Add a near-duplicate
        memory_vault.batch_upsert_chunks([{
            "content_hash": "mem1_dup",
            "content": "def authenticate(user, password):\n    return check_credentials(user, password)",
            "file_path": "auth_copy.py",
            "file_hash": "f_dup",
            "wing": "api",
            "room": "auth",
            "generation": 1,
        }])
        stack = MemoryStack(memory_vault, TokenBudget(l1_max=5000))
        text, report = stack._load_l1()
        assert report.chunks_skipped_dedup >= 1

    def test_wing_filter(self, memory_vault, no_identity):
        """Passing wing should filter L1 chunks."""
        stack = MemoryStack(memory_vault, TokenBudget(l1_max=5000))
        text, report = stack._load_l1(wing="docs")
        # Should only load docs-wing chunks
        if text:
            assert "README" in text or "Project" in text


class TestRecall:
    """Test L2 on-demand recall."""

    def test_returns_chunks(self, memory_vault):
        """Recall should return chunks from the vault."""
        stack = MemoryStack(memory_vault)
        result = stack.recall()
        assert "text" in result
        assert "report" in result
        assert "results" in result
        assert result["report"].chunks_loaded > 0

    def test_wing_filter(self, memory_vault):
        """Recall with wing filter should only return matching chunks."""
        stack = MemoryStack(memory_vault)
        result = stack.recall(wing="docs")
        for chunk in result["results"]:
            assert chunk["wing"] == "docs"

    def test_room_filter(self, memory_vault):
        """Recall with room filter should only return matching chunks."""
        stack = MemoryStack(memory_vault)
        result = stack.recall(room="database")
        for chunk in result["results"]:
            assert chunk["room"] == "database"

    def test_combined_filters(self, memory_vault):
        """Both wing and room filters should work together."""
        stack = MemoryStack(memory_vault)
        result = stack.recall(wing="api", room="auth")
        for chunk in result["results"]:
            assert chunk["wing"] == "api"
            assert chunk["room"] == "auth"

    def test_empty_vault_returns_empty(self, tmp_vault):
        """Recall on an empty vault should return empty results."""
        stack = MemoryStack(tmp_vault)
        result = stack.recall()
        assert result["report"].chunks_loaded == 0


class TestSearch:
    """Test L3 deep hybrid search integration."""

    def test_delegates_to_hybrid_search(self, memory_vault):
        """Search should return results from hybrid_search."""
        stack = MemoryStack(memory_vault)
        result = stack.search("authenticate")
        assert "text" in result
        assert "report" in result
        assert "results" in result

    def test_report_layer_is_l3(self, memory_vault):
        """Report should be tagged as L3."""
        stack = MemoryStack(memory_vault)
        result = stack.search("database")
        assert result["report"].layer == "L3"

    def test_tokens_counted(self, memory_vault):
        """Report should include token usage."""
        stack = MemoryStack(memory_vault)
        result = stack.search("database")
        if result["results"]:
            assert result["report"].tokens_used > 0


class TestFormatting:
    """Test output formatting methods."""

    def test_format_chunks_empty(self, memory_vault):
        """Empty chunk list should produce empty string."""
        stack = MemoryStack(memory_vault)
        assert stack._format_chunks([]) == ""

    def test_format_chunks_includes_header(self, memory_vault):
        """Formatted chunks should include wing/room/file_path header."""
        stack = MemoryStack(memory_vault)
        chunks = [{"wing": "api", "room": "auth", "file_path": "auth.py", "content": "code here"}]
        text = stack._format_chunks(chunks)
        assert "[api/auth]" in text
        assert "auth.py" in text

    def test_format_search_results_empty(self, memory_vault):
        """Empty result list should produce empty string."""
        stack = MemoryStack(memory_vault)
        assert stack._format_search_results([]) == ""

    def test_format_search_results_includes_score(self, memory_vault):
        """Formatted search results should include score."""
        stack = MemoryStack(memory_vault)
        results = [
            {"wing": "w", "room": "r", "file_path": "f.py", "content": "code",
             "score": 0.5, "sources": ["semantic"]},
        ]
        text = stack._format_search_results(results)
        assert "0.5" in text
        assert "semantic" in text
