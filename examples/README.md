# Examples

Practical examples showing how to use EngramKit.

## Quick Start

```bash
# Mine a repo and search it
python examples/01_quickstart.py /path/to/your/repo

# Compare semantic vs keyword vs hybrid search
python examples/02_hybrid_search.py /path/to/repo "your query"
```

## All Examples

| # | File | Description |
|---|------|-------------|
| 01 | `01_quickstart.py` | Mine a repo, search it, check status |
| 02 | `02_hybrid_search.py` | Compare semantic vs BM25 vs hybrid search |
| 03 | `03_knowledge_graph.py` | Add facts, query entities, view timeline |
| 04 | `04_gc_lifecycle.py` | Mine, edit, re-mine, and GC stale chunks |
| 05 | `05_memory_layers.py` | L0/L1/L2/L3 memory with token budgets |
| 06 | `06_mcp_setup.md` | Connect EngramKit to Claude Code via MCP |
| 07 | `07_secret_scanning.py` | How secret detection works |
| 08 | `08_content_hooks.py` | Content-aware importance scoring |

## Prerequisites

```bash
cd /path/to/engramkit
pip install -e .
```

Most examples require a mined repo. Run `01_quickstart.py` first to create one.
