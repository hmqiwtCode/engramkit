"""Comprehensive tests for the MCP JSON-RPC server — all 12 tools."""

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from engramkit.mcp.server import (
    handle_jsonrpc,
    handle_status,
    handle_search,
    handle_wake_up,
    handle_recall,
    handle_save,
    handle_kg_add,
    handle_kg_query,
    handle_kg_timeline,
    handle_kg_invalidate,
    handle_diary_write,
    handle_gc,
    handle_config,
    TOOLS,
    HANDLERS,
)
from engramkit.storage.vault import Vault, VaultManager


@pytest.fixture
def mcp_vault(tmp_path, monkeypatch):
    """Set up ENGRAMKIT_HOME and create a vault the MCP server can find."""
    engramkit_home = tmp_path / "engramkit_mcp"
    engramkit_home.mkdir()
    (engramkit_home / "identity.txt").write_text("Test identity for MCP tests.")
    monkeypatch.setattr("engramkit.config.ENGRAMKIT_HOME", engramkit_home)
    monkeypatch.setattr("engramkit.storage.vault.ENGRAMKIT_HOME", engramkit_home)
    monkeypatch.setattr("engramkit.mcp.server.ENGRAMKIT_HOME", engramkit_home)
    monkeypatch.setattr("engramkit.memory.layers.ENGRAMKIT_HOME", engramkit_home)

    # Create a test vault via VaultManager
    repo_path = str(tmp_path / "test_repo")
    os.makedirs(repo_path, exist_ok=True)
    vault = VaultManager.get_vault(repo_path)

    # Seed some data
    vault.batch_upsert_chunks([
        {
            "content_hash": "mcp1",
            "content": "def process_payment(amount):\n    return stripe.charge(amount)",
            "file_path": "payments.py",
            "file_hash": "fh1",
            "wing": "api",
            "room": "payments",
            "generation": 1,
        },
        {
            "content_hash": "mcp2",
            "content": "class NotificationService:\n    def send(self, user, msg): pass",
            "file_path": "notify.py",
            "file_hash": "fh2",
            "wing": "api",
            "room": "notifications",
            "generation": 1,
        },
    ])
    vault.close()

    return {"engramkit_home": engramkit_home, "repo_path": repo_path}


def _jsonrpc(method, params=None, req_id=1):
    """Helper to create a JSON-RPC request."""
    return {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}}


def _tool_call(name, arguments=None, req_id=1):
    """Helper to create a tools/call request."""
    return _jsonrpc("tools/call", {"name": name, "arguments": arguments or {}}, req_id)


class TestMCPProtocol:
    """Verify JSON-RPC protocol handling."""

    def test_initialize(self):
        """Initialize should return server info."""
        resp = handle_jsonrpc(_jsonrpc("initialize"))
        assert resp["result"]["serverInfo"]["name"] == "engramkit"
        assert "protocolVersion" in resp["result"]

    def test_tools_list_returns_12_tools(self):
        """tools/list should return exactly 12 tools."""
        resp = handle_jsonrpc(_jsonrpc("tools/list"))
        tools = resp["result"]["tools"]
        assert len(tools) == 12

    def test_tools_list_names(self):
        """Verify all expected tool names are present."""
        resp = handle_jsonrpc(_jsonrpc("tools/list"))
        names = {t["name"] for t in resp["result"]["tools"]}
        expected = {
            "engramkit_status", "engramkit_search", "engramkit_wake_up", "engramkit_recall",
            "engramkit_kg_query", "engramkit_kg_timeline", "engramkit_save", "engramkit_kg_add",
            "engramkit_kg_invalidate", "engramkit_diary_write", "engramkit_gc", "engramkit_config",
        }
        assert names == expected

    def test_unknown_method_returns_error(self):
        """Unknown JSON-RPC methods should return an error response."""
        resp = handle_jsonrpc(_jsonrpc("foo/bar"))
        assert "error" in resp
        assert resp["error"]["code"] == -32601

    def test_unknown_tool_returns_error(self):
        """Calling an unknown tool should return an error."""
        resp = handle_jsonrpc(_tool_call("nonexistent_tool"))
        assert "error" in resp

    def test_notification_no_response(self):
        """Notifications (no id) should return None."""
        resp = handle_jsonrpc({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        })
        assert resp is None

    def test_response_has_jsonrpc_field(self):
        """All responses should include jsonrpc version."""
        resp = handle_jsonrpc(_jsonrpc("initialize"))
        assert resp["jsonrpc"] == "2.0"

    def test_response_has_matching_id(self):
        """Response id should match request id."""
        resp = handle_jsonrpc(_jsonrpc("initialize", req_id=42))
        assert resp["id"] == 42


class TestEngramKitStatus:
    """Test engramkit_status tool."""

    def test_returns_stats(self, mcp_vault):
        """Status should return vault statistics."""
        resp = handle_jsonrpc(_tool_call("engramkit_status", {"repo_path": mcp_vault["repo_path"]}))
        result = json.loads(resp["result"]["content"][0]["text"])
        assert "total_chunks" in result
        assert result["total_chunks"] == 2

    def test_includes_wing_rooms(self, mcp_vault):
        """Stats should include wing/room breakdown."""
        resp = handle_jsonrpc(_tool_call("engramkit_status", {"repo_path": mcp_vault["repo_path"]}))
        result = json.loads(resp["result"]["content"][0]["text"])
        assert "wing_rooms" in result


class TestEngramKitSearch:
    """Test engramkit_search tool."""

    def test_returns_results(self, mcp_vault):
        """Search should return matching results."""
        resp = handle_jsonrpc(_tool_call("engramkit_search", {
            "query": "process_payment",
            "repo_path": mcp_vault["repo_path"],
        }))
        result = json.loads(resp["result"]["content"][0]["text"])
        assert result["count"] >= 1

    def test_with_wing_filter(self, mcp_vault):
        """Search with wing filter should work."""
        resp = handle_jsonrpc(_tool_call("engramkit_search", {
            "query": "payment",
            "repo_path": mcp_vault["repo_path"],
            "wing": "api",
        }))
        result = json.loads(resp["result"]["content"][0]["text"])
        assert isinstance(result["results"], list)


class TestEngramKitWakeUp:
    """Test engramkit_wake_up tool."""

    def test_returns_context(self, mcp_vault):
        """Wake up should return context text and token info."""
        resp = handle_jsonrpc(_tool_call("engramkit_wake_up", {
            "repo_path": mcp_vault["repo_path"],
        }))
        result = json.loads(resp["result"]["content"][0]["text"])
        assert "context" in result
        assert "total_tokens" in result
        assert "l0" in result
        assert "l1" in result

    def test_l1_tokens_parameter(self, mcp_vault):
        """Custom l1_tokens budget should be accepted."""
        resp = handle_jsonrpc(_tool_call("engramkit_wake_up", {
            "repo_path": mcp_vault["repo_path"],
            "l1_tokens": 500,
        }))
        result = json.loads(resp["result"]["content"][0]["text"])
        assert result["l1"]["budget"] == 500


class TestEngramKitRecall:
    """Test engramkit_recall tool."""

    def test_returns_text(self, mcp_vault):
        """Recall should return recalled text."""
        resp = handle_jsonrpc(_tool_call("engramkit_recall", {
            "repo_path": mcp_vault["repo_path"],
        }))
        result = json.loads(resp["result"]["content"][0]["text"])
        assert "text" in result
        assert "chunks_loaded" in result


class TestEngramKitSave:
    """Test engramkit_save tool."""

    def test_saves_content(self, mcp_vault):
        """Save should store content and return content_hash."""
        resp = handle_jsonrpc(_tool_call("engramkit_save", {
            "content": "Important architectural decision: use event sourcing.",
            "repo_path": mcp_vault["repo_path"],
        }))
        result = json.loads(resp["result"]["content"][0]["text"])
        assert result["saved"] is True
        assert "content_hash" in result
        assert "tokens" in result

    def test_deduplicates_by_hash(self, mcp_vault):
        """Saving identical content twice should produce the same hash."""
        content = "Exactly the same content for dedup test."
        resp1 = handle_jsonrpc(_tool_call("engramkit_save", {
            "content": content,
            "repo_path": mcp_vault["repo_path"],
        }))
        resp2 = handle_jsonrpc(_tool_call("engramkit_save", {
            "content": content,
            "repo_path": mcp_vault["repo_path"],
        }))
        r1 = json.loads(resp1["result"]["content"][0]["text"])
        r2 = json.loads(resp2["result"]["content"][0]["text"])
        assert r1["content_hash"] == r2["content_hash"]

    def test_custom_wing_and_room(self, mcp_vault):
        """Save with custom wing and room should work."""
        resp = handle_jsonrpc(_tool_call("engramkit_save", {
            "content": "Test content",
            "repo_path": mcp_vault["repo_path"],
            "wing": "custom_wing",
            "room": "custom_room",
        }))
        result = json.loads(resp["result"]["content"][0]["text"])
        assert result["saved"] is True


class TestEngramKitKG:
    """Test knowledge graph tools: add, query, timeline, invalidate."""

    def test_kg_add(self, mcp_vault):
        """Adding a triple should succeed."""
        resp = handle_jsonrpc(_tool_call("engramkit_kg_add", {
            "subject": "ServiceA",
            "predicate": "depends_on",
            "object": "ServiceB",
            "repo_path": mcp_vault["repo_path"],
        }))
        result = json.loads(resp["result"]["content"][0]["text"])
        assert result["added"] is True
        assert "triple_id" in result

    def test_kg_query(self, mcp_vault):
        """Querying an entity should return its facts."""
        # First add a triple
        handle_jsonrpc(_tool_call("engramkit_kg_add", {
            "subject": "Alice",
            "predicate": "works_at",
            "object": "Company",
            "repo_path": mcp_vault["repo_path"],
        }))
        # Then query
        resp = handle_jsonrpc(_tool_call("engramkit_kg_query", {
            "entity": "Alice",
            "repo_path": mcp_vault["repo_path"],
        }))
        result = json.loads(resp["result"]["content"][0]["text"])
        assert result["count"] >= 1

    def test_kg_timeline(self, mcp_vault):
        """Timeline should return chronological facts."""
        handle_jsonrpc(_tool_call("engramkit_kg_add", {
            "subject": "Team",
            "predicate": "adopted",
            "object": "Kubernetes",
            "repo_path": mcp_vault["repo_path"],
            "valid_from": "2025-01-01",
        }))
        resp = handle_jsonrpc(_tool_call("engramkit_kg_timeline", {
            "repo_path": mcp_vault["repo_path"],
        }))
        result = json.loads(resp["result"]["content"][0]["text"])
        assert "timeline" in result

    def test_kg_invalidate(self, mcp_vault):
        """Invalidating a triple should mark it as ended."""
        handle_jsonrpc(_tool_call("engramkit_kg_add", {
            "subject": "Dev",
            "predicate": "uses",
            "object": "OldDB",
            "repo_path": mcp_vault["repo_path"],
        }))
        resp = handle_jsonrpc(_tool_call("engramkit_kg_invalidate", {
            "subject": "Dev",
            "predicate": "uses",
            "object": "OldDB",
            "repo_path": mcp_vault["repo_path"],
            "ended": "2026-01-01",
        }))
        result = json.loads(resp["result"]["content"][0]["text"])
        assert result["invalidated"] is True


class TestEngramKitDiary:
    """Test engramkit_diary_write tool."""

    def test_diary_write(self, mcp_vault):
        """Diary entry should be saved successfully."""
        resp = handle_jsonrpc(_tool_call("engramkit_diary_write", {
            "content": "Today I helped debug a database connection issue.",
            "repo_path": mcp_vault["repo_path"],
        }))
        result = json.loads(resp["result"]["content"][0]["text"])
        assert result["saved"] is True
        assert "content_hash" in result


class TestEngramKitGC:
    """Test engramkit_gc tool."""

    def test_gc_completes(self, mcp_vault):
        """GC should run without error."""
        resp = handle_jsonrpc(_tool_call("engramkit_gc", {
            "repo_path": mcp_vault["repo_path"],
            "retention_days": 30,
        }))
        result = json.loads(resp["result"]["content"][0]["text"])
        assert result["completed"] is True


class TestEngramKitConfig:
    """Test engramkit_config get/set tool."""

    def test_config_set(self, mcp_vault):
        """Setting a config value should succeed."""
        resp = handle_jsonrpc(_tool_call("engramkit_config", {
            "key": "test_key",
            "value": "test_value",
            "repo_path": mcp_vault["repo_path"],
        }))
        result = json.loads(resp["result"]["content"][0]["text"])
        assert result["set"] is True
        assert result["value"] == "test_value"

    def test_config_get(self, mcp_vault):
        """Getting a config value should return the stored value."""
        # Set first
        handle_jsonrpc(_tool_call("engramkit_config", {
            "key": "test_key",
            "value": "test_value",
            "repo_path": mcp_vault["repo_path"],
        }))
        # Then get
        resp = handle_jsonrpc(_tool_call("engramkit_config", {
            "key": "test_key",
            "repo_path": mcp_vault["repo_path"],
        }))
        result = json.loads(resp["result"]["content"][0]["text"])
        assert result["value"] == "test_value"

    def test_config_get_missing_key(self, mcp_vault):
        """Getting a nonexistent key should return null."""
        resp = handle_jsonrpc(_tool_call("engramkit_config", {
            "key": "nonexistent",
            "repo_path": mcp_vault["repo_path"],
        }))
        result = json.loads(resp["result"]["content"][0]["text"])
        assert result["value"] is None


class TestErrorHandling:
    """Verify error handling for tool calls."""

    def test_tool_exception_returns_error_content(self, mcp_vault):
        """Tool exceptions should be caught and returned as error content."""
        # engramkit_search without 'query' should fail
        resp = handle_jsonrpc(_tool_call("engramkit_search", {
            "repo_path": mcp_vault["repo_path"],
            # Missing 'query'
        }))
        # Should return a response with isError flag
        assert resp["result"]["isError"] is True

    def test_handlers_dict_complete(self):
        """HANDLERS dict should have an entry for each TOOL name."""
        tool_names = {t["name"] for t in TOOLS}
        handler_names = set(HANDLERS.keys())
        assert tool_names == handler_names
