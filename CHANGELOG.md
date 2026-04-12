# EngramKit Changelog

## v0.1.2 -- 2026-04-13

### Fixes

- PyPI project URLs now point at the real GitHub repo (previously placeholder `user/engramkit`).
- README images render on PyPI — switched from repo-relative paths to absolute `raw.githubusercontent.com` URLs so the logo, architecture diagram, and screenshots show up on the project page.

## v0.1.1 -- 2026-04-12

- First public release on PyPI via GitHub Actions trusted publishing.

## v0.1.0 -- 2026-04-09

Initial release.

### Features

- **Content-addressed storage** using SHA256 chunk IDs for deduplication and edit stability.
- **Hybrid search** combining ChromaDB semantic search with SQLite FTS5 BM25, fused via Reciprocal Rank Fusion.
- **Git-aware mining** using `git diff` for incremental ingestion; re-mine in ~0.1s when nothing changed.
- **Generation-based garbage collection** with configurable retention and full audit logging.
- **Secret filtering** for `.env`, credential files, API keys, tokens, and private keys.
- **Smart 800-char chunker** with boundary detection at blank lines, function definitions, and class declarations.
- **4-layer memory stack** (L0 identity, L1 essential, L2 on-demand, L3 deep search) with token budgets.
- **Recency + importance scoring** with exponential decay and access frequency boost for L1 context loading.
- **Exact token counting** via tiktoken (cl100k_base).
- **Temporal knowledge graph** with entity-relationship triples, `valid_from`/`valid_to`, and timeline queries.
- **Content-aware hook triggers** with signal detection (decisions, architecture, problems solved, planning).
- **MCP server** with 12 tools for Claude, ChatGPT, and other MCP-compatible assistants.
- **FastAPI REST API** with endpoints for search, vaults, memory, knowledge graph, and RAG chat.
- **Next.js dashboard** with chat, search, vault management, knowledge graph explorer, and GC controls.
- **CLI** with commands: `init`, `mine`, `search`, `status`, `wake-up`, `gc`, `hooks`.
- **Git hooks** for automatic mining on commit and pull.
- **69 passing tests** covering vault operations, chunking, search, token budgets, knowledge graph, hooks, MCP, and secret scanning.
