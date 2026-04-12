"""Tests for MCP server."""


from engramkit.mcp.server import handle_jsonrpc


class TestMCPProtocol:
    def test_initialize(self):
        resp = handle_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        assert resp["result"]["serverInfo"]["name"] == "engramkit"

    def test_list_tools(self):
        resp = handle_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        tools = resp["result"]["tools"]
        assert len(tools) == 12
        names = {t["name"] for t in tools}
        assert "engramkit_search" in names
        assert "engramkit_save" in names
        assert "engramkit_gc" in names

    def test_unknown_method(self):
        resp = handle_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "foo/bar", "params": {}})
        assert "error" in resp

    def test_unknown_tool(self):
        resp = handle_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                               "params": {"name": "nonexistent", "arguments": {}}})
        assert "error" in resp

    def test_notification_no_response(self):
        resp = handle_jsonrpc({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        assert resp is None
