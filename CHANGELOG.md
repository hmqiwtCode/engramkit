# EngramKit Changelog

## v0.2.2 -- 2026-04-15

Republishes v0.2.1 with the bundled dashboard rebuilt. v0.2.1 to PyPI shipped with a stale `engramkit/dashboard_static/` — the wheel had the new agentic backend but the old chat UI, because the release workflow did not run the dashboard build script. PyPI versions are immutable, so v0.2.2 is the corrected artifact. Source code unchanged versus v0.2.1; rebuild + workflow hardening only.

### Fixed

- **Bundled dashboard now matches the source.** The release workflow runs `setup-node@v4` + `npm ci` + `./scripts/build-dashboard.sh` before `python -m build`, so the wheel always packages a freshly-built UI. `scripts/build-dashboard.sh` also forces `NEXT_PUBLIC_ENGRAMKIT_API_URL=""` during the build so a developer's local `.env.local` (often pointing at `http://localhost:8000` for split-process dev) cannot leak into shipped JS — the bundled dashboard is served same-origin by the Python API.
- **Release skill (`.claude/skills/release/SKILL.md`) updated** to add a step 3c that rebuilds the bundled dashboard and stages any diff in `engramkit/dashboard_static/`. Defense in depth — workflow auto-rebuilds AND the skill reminds the human.

## v0.2.1 -- 2026-04-15

### Added

- **Agentic chat endpoint.** `/api/chat` wires the engramkit MCP toolset (search, recall, kg_query, kg_timeline, wake_up, status, save, kg_add, diary_write) into the Claude Agent SDK loop so the assistant can iterate over memory tools instead of answering off a single pre-search. New SSE events stream tool inputs and results so the dashboard can surface them live.
- **Inline citations in the chat UI (Perplexity-style).** Assistant messages can cite chunks with `[^N]` markers that render as indigo superscript pills. Hover shows a Radix HoverCard preview (file, score, wing badge, content); click smooth-scrolls to a registry-driven references panel below the message. Raw file paths in the prose are also auto-linked when they match a known chunk. Unresolved citations render as muted gray chips so trust gaps are explicit.
- **Per-tool result renderers in the chat bubble.** `engramkit_search` renders as clickable chunk cards, `engramkit_kg_query` as fact rows, `engramkit_recall` per-repo, `Read`/`Grep`/`Glob` as structured views, fallback as a collapsible JSON tree.

### Changed

- **Chat UI rebuilt as a modular tree.** Single 960-line `chat.tsx` split into a focused `views/chat/` module: types, hooks (sessions, stream, citation registry, vault list, streaming bubble), lib (storage, tool summary, stream store), and presentation components. Each file <300 lines except the renderer dispatch table.
- **Streaming uses an external store.** The in-flight assistant bubble lives in a `useSyncExternalStore`-backed singleton; committed messages are memo'd and never re-render during streaming. Per-turn React state updates dropped from ~200 to 2.
- **Inline tool-call timeline.** Tool events interleave chronologically inside the assistant bubble (collapsible) instead of clustering at the bottom — users can see what the agent did to reach an answer.

### Fixed

- **Hydration mismatch on first render.** `useChatSessions` no longer reads `localStorage` in `useState`; it hydrates in `useEffect` so SSR and first client render agree on session count.
- **Next 16 dev compatibility.** `[[...slug]]/page.tsx` enumerates all top-level routes in `generateStaticParams` (required by `output: "export"` — `/chat`, `/search`, `/settings`, `/vaults` were 500ing). Added `suppressHydrationWarning` on `<html>` for font CSS hash drift and browser-extension attribute injection.
- **POST `/api/chat` no longer hits the dashboard origin.** Chat stream reads `NEXT_PUBLIC_ENGRAMKIT_API_URL` like other API calls; previously the relative URL was rewritten to `/api/chat/` by `trailingSlash: true` and trapped by the SPA catch-all, returning 500.
- **Aborted tool calls commit cleanly.** Hitting Stop mid-search stamps the in-flight tool call with `result: "(aborted)"` / `isError: true` instead of leaving forever-pending dots persisted into localStorage.

## v0.1.5 -- 2026-04-14

### Added

- **`engramkit -v` / `--version`** — print the installed version and exit. Resolves via `importlib.metadata`, so `pyproject.toml` is the single source of truth and `__version__` no longer drifts.

## v0.1.4 -- 2026-04-13

### Fixed

- **Claude Code hooks now fire reliably across Python installs.** Previously the plugin's hooks called `python3 -m engramkit.hooks.claude_hook_handler`, which resolved to whatever `python3` was first on PATH — often a Homebrew/system Python that didn't have engramkit installed, causing the `SessionStart` hook to silently do nothing. Replaced with a new `engramkit-hook` console-script entry point that ships in the same bin/ directory as `engramkit-mcp`, so it always runs with the correct interpreter.

### Changed

- **Plugin hooks no longer ship bash wrappers.** `hooks/engramkit-*.sh` are gone; `hooks/hooks.json` now invokes `engramkit-hook <event>` directly. Simpler structure, one less indirection.

## v0.1.3 -- 2026-04-13

### Added

- **`engramkit mine --ignore`** — skip extra folders per invocation. Accepts gitignore-style patterns via `pathspec`: `docs` (any depth), `/docs` (root only), `lib/docs` (anchored), `lib/**` (recursive), `*.log`, `!keep.md` (negation). Merges with the project's `.gitignore` into a single PathSpec.
- **Claude Code plugin** — `/plugin marketplace add hmqiwtCode/engramkit` then `/plugin install engramkit@engramkit` wires the MCP server plus `SessionStart`, `Stop`, and `PreCompact` hooks in one command. No `settings.json` editing.
- **SessionStart hook** — runs `engramkit wake-up` on every Claude Code session and injects identity + L1 essential memory (~170 tokens) directly into context. Claude starts each session already primed with project memory — no tool call required.
- **Protocol embedded in `engramkit_wake_up`** — the tool response now includes imperative instructions (search before guessing, save after decisions) so every call re-teaches Claude the memory-use rules.

### Changed

- **`version` single source of truth** — `scripts/sync-version.py` rewrites `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` from `pyproject.toml`. CI + release workflow guard against drift.

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
