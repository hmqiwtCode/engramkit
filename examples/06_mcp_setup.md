# MCP Setup Guide

Connect EngramKit to Claude Code, ChatGPT, or other MCP-compatible AI tools.

## Claude Code

```bash
# Register EngramKit as an MCP server
claude mcp add engramkit -- python -m engramkit.mcp.server

# Verify it's registered
claude mcp list
```

Once registered, Claude has access to 12 EngramKit tools:

| Tool | Description |
|------|-------------|
| `engramkit_status` | Vault overview |
| `engramkit_search` | Hybrid search |
| `engramkit_wake_up` | Load L0+L1 context |
| `engramkit_recall` | L2 on-demand recall |
| `engramkit_kg_query` | Knowledge graph query |
| `engramkit_kg_timeline` | Fact timeline |
| `engramkit_save` | Save content to vault |
| `engramkit_kg_add` | Add fact |
| `engramkit_kg_invalidate` | Expire fact |
| `engramkit_diary_write` | Agent journal |
| `engramkit_gc` | Garbage collection |
| `engramkit_config` | Get/set config |

## Usage in Claude Code

After setup, Claude automatically uses EngramKit tools when you ask about your codebase:

```
You: "How does the search system work?"

Claude:
  → Calls engramkit_search("search system")
  → Gets 5 relevant code chunks
  → Answers with specific file references
```

## Dashboard (Web UI)

For a visual interface:

```bash
# Terminal 1: API server
python -m engramkit.api.server

# Terminal 2: Dashboard
cd dashboard && npm run dev
```

Open http://localhost:3000 for the full dashboard with chat, search, vaults, and knowledge graph.
