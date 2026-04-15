"""RAG chat endpoint — iterative engramkit search + stream via Claude Agent SDK."""

import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from engramkit.search.hybrid import hybrid_search
from engramkit.api.helpers import get_vault_by_id, ChatRequest
from engramkit.api.chat_tools import build_engramkit_mcp_server, ENGRAMKIT_TOOL_NAMES

router = APIRouter(prefix="/api", tags=["chat"])

# File tools the agent also needs for reading raw source when memory is insufficient.
FILE_TOOLS = ["Read", "Grep", "Glob"]


def _format_history(history: list) -> str:
    if not history:
        return ""
    lines = ["## Conversation History:"]
    for h in history[-10:]:
        role = h.get("role", "user")
        content = h.get("content", "")[:500]
        lines.append(f"**{role}:** {content}")
    lines.append("")
    return "\n".join(lines) + "\n"


def _extract_usage(msg):
    input_tokens = output_tokens = cache_read = 0
    msg_usage = getattr(msg, 'usage', None)
    if isinstance(msg_usage, dict):
        input_tokens = msg_usage.get('input_tokens', 0) or 0
        output_tokens = msg_usage.get('output_tokens', 0) or 0
        cache_read = msg_usage.get('cache_read_input_tokens', 0) or 0
    if input_tokens == 0:
        for md in (getattr(msg, 'model_usage', None) or {}).values():
            if isinstance(md, dict):
                input_tokens += md.get('inputTokens', 0) or 0
                output_tokens += md.get('outputTokens', 0) or 0
                cache_read += md.get('cacheReadInputTokens', 0) or 0
    return input_tokens, output_tokens, cache_read


def _short_tool_name(name: str) -> str:
    """Strip the `mcp__<server>__` prefix so the UI shows the bare tool name."""
    if name.startswith("mcp__"):
        parts = name.split("__", 2)
        if len(parts) == 3:
            return parts[2]
    return name


def _summarise_tool_result(content) -> str:
    """Flatten a ToolResultBlock content payload into a preview string."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(item.get("text") or json.dumps(item, default=str))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)


@router.post("/chat")
async def chat(req: ChatRequest):
    vault_ids = req.vault_ids or ([req.vault_id] if req.vault_id else [])
    if not vault_ids:
        raise HTTPException(400, "No vault selected")

    repo_names, repo_paths = [], []
    for vid in vault_ids:
        vault = get_vault_by_id(vid)
        try:
            rp = vault.get_meta("repo_path", "unknown")
            repo_names.append(rp.split("/")[-1] if rp else vid)
            if rp:
                repo_paths.append(rp)
        finally:
            vault.close()

    repo_name = ", ".join(repo_names)

    results = []
    if req.mode == "rag":
        for vid in vault_ids:
            vault = get_vault_by_id(vid)
            try:
                hits = hybrid_search(req.message, vault, n_results=req.n_context)
                rp = vault.get_meta("repo_path", "unknown")
                rn = rp.split("/")[-1] if rp else vid
                for r in hits:
                    r["_repo"] = rn
                results.extend(hits)
            finally:
                vault.close()

        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        results = results[:req.n_context]

        context_chunks = [
            f"[{r.get('_repo', '')}/{r['file_path']}] (score: {r['score']:.4f})\n{r['content']}"
            for r in results
        ]
        context = "\n\n---\n\n".join(context_chunks) if context_chunks else "No seed results."

        pinned = ""
        if req.pinned_chunks:
            pinned = "\n\n---\n\n".join(
                f"[{pc.get('file','?')}] (pinned)\n{pc.get('content','')}"
                for pc in req.pinned_chunks
            )

        full_context = (
            f"## Pinned:\n{pinned}\n\n## Auto-Retrieved (seed):\n{context}"
            if pinned else context
        )

        prompt = f"""You are a code + memory assistant for the "{repo_name}" codebase.

You have a seed hybrid-search result below, PLUS live access to iterative tools.
Do not stop at the seed — treat it as a starting point and pull more context as you reason.

AVAILABLE TOOLS
- engramkit_search(query, wing?, room?, n_results?) — additional targeted hybrid searches; call
  several times with different phrasings to triangulate, or narrow with wing/room.
- engramkit_recall(wing?, room?, n_results?) — grab recent context in a topic area (recency × importance).
- engramkit_kg_query(entity, as_of?, direction?) — entity relationships from the knowledge graph.
- engramkit_kg_timeline(entity?) — chronological facts about an entity (or all).
- engramkit_wake_up(wing?) — L0 identity + L1 essential context (use for complex multi-step asks).
- engramkit_status() — vault overview if you need sizing / inventory.
- Read / Grep / Glob — fall back to raw file inspection when the vault clearly lacks the answer.
- engramkit_save / engramkit_kg_add / engramkit_diary_write — persist important conclusions after the answer.

HOW TO WORK
1. Scan the seed results. If they fully answer the question, respond directly.
2. If not, call engramkit_search / recall / kg_query iteratively — multiple calls are expected and encouraged.
3. Only touch Read / Grep / Glob when memory tools can't resolve the question.
4. Cite specific file paths. Be concise. No filler.

CITATIONS — IMPORTANT FOR USER TRUST
- When you make a factual claim grounded in a specific chunk, append a footnote marker `[^N]` where N is the 1-indexed position of that chunk in the Seed Results list below (or the chunk's position in a tool result).
- The UI renders each `[^N]` as a clickable pill that scrolls to the exact chunk, so the user can verify. Miscited markers undermine trust — only cite when you are actually using that chunk.
- Multiple markers per sentence are fine when combining evidence: `…as handled in the router [^1][^3].`
- Do NOT invent markers beyond the chunks actually present. If you don't have grounding for a claim, say so explicitly instead of fabricating a citation.
- You do not need to write a "References" section — the UI builds one automatically from your markers.

## Seed Results ({len(results)} chunks):
{full_context}

{_format_history(req.history)}## Question:
{req.message}"""

    else:
        prompt = f"""You are a code + memory assistant for the "{repo_name}" codebase.

You have live access to engramkit memory tools and file tools — no pre-search was run.

AVAILABLE TOOLS
- engramkit_wake_up() — start here for non-trivial questions to load identity + essential context.
- engramkit_search(query, ...) — hybrid search; call multiple times with different queries.
- engramkit_recall(wing?, room?) — pull recent context by topic.
- engramkit_kg_query(entity) / engramkit_kg_timeline(entity?) — knowledge graph.
- engramkit_status() — vault overview.
- Read / Grep / Glob — raw file inspection when memory is insufficient.
- engramkit_save / engramkit_kg_add / engramkit_diary_write — persist conclusions.

Be iterative. Run several tool calls, refine, then answer. Cite file paths. Be concise.

CITATIONS — IMPORTANT FOR USER TRUST
- When you make a factual claim grounded in a specific chunk returned by engramkit_search (or engramkit_recall), append a footnote marker `[^N]` where N is the 1-indexed position of that chunk across all your tool results.
- The UI renders each `[^N]` as a clickable pill that scrolls to the exact chunk, so the user can verify. Miscited markers undermine trust — only cite when you are actually using that chunk.
- Do NOT invent markers for chunks that don't exist. If you don't have grounding, say so explicitly.
- You do not need to write a "References" section — the UI builds one automatically.

{_format_history(req.history)}## Question:
{req.message}"""

    async def generate():
        try:
            from claude_agent_sdk import (
                query as sdk_query, ClaudeAgentOptions,
                AssistantMessage, UserMessage, TextBlock, ToolUseBlock, ToolResultBlock,
                ResultMessage, StreamEvent,
            )
        except ImportError:
            yield f"data: {json.dumps({'type': 'text', 'text': 'Error: chat feature requires the [chat] extra. Install with: pip install engramkit[chat]'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        yield f"data: {json.dumps({'type': 'mode', 'mode': req.mode})}\n\n"

        if results:
            sources = [{
                "file": r.get("file_path", "?"),
                "score": r.get("score", 0),
                "content": r.get("content", ""),
                "wing": r.get("wing", ""),
                "room": r.get("room", ""),
                "content_hash": r.get("content_hash", ""),
            } for r in results]
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

        engramkit_server = build_engramkit_mcp_server(repo_paths)

        got_content = False
        tool_calls = 0
        tool_use_index: dict[str, int] = {}

        try:
            async for msg in sdk_query(
                prompt=prompt,
                options=ClaudeAgentOptions(
                    max_turns=None,
                    permission_mode="auto",
                    model=req.model or None,
                    include_partial_messages=True,
                    cwd=repo_paths[0] if repo_paths else None,
                    mcp_servers={"engramkit": engramkit_server},
                    allowed_tools=[*FILE_TOOLS, *ENGRAMKIT_TOOL_NAMES],
                ),
            ):
                if isinstance(msg, StreamEvent):
                    event = msg.event if hasattr(msg, 'event') else {}
                    if isinstance(event, dict) and event.get("type") == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta" and delta.get("text"):
                            got_content = True
                            yield f"data: {json.dumps({'type': 'text', 'text': delta['text']})}\n\n"

                elif isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, ToolUseBlock):
                            tool_calls += 1
                            idx = tool_calls - 1
                            tool_use_index[block.id] = idx
                            short = _short_tool_name(block.name)
                            is_engramkit = block.name.startswith("mcp__engramkit__")
                            payload = {
                                "type": "tool_call",
                                "tool": short,
                                "full_name": block.name,
                                "input": block.input,
                                "is_engramkit": is_engramkit,
                                "index": idx,
                                "count": tool_calls,
                            }
                            yield f"data: {json.dumps(payload, default=str)}\n\n"
                        elif isinstance(block, TextBlock) and block.text and not got_content:
                            got_content = True
                            yield f"data: {json.dumps({'type': 'text', 'text': block.text})}\n\n"

                elif isinstance(msg, UserMessage):
                    content = msg.content
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, ToolResultBlock):
                                idx = tool_use_index.get(block.tool_use_id)
                                preview = _summarise_tool_result(block.content)
                                if len(preview) > 4000:
                                    preview = preview[:4000] + "\n…[truncated]"
                                payload = {
                                    "type": "tool_result",
                                    "index": idx,
                                    "tool_use_id": block.tool_use_id,
                                    "is_error": bool(block.is_error),
                                    "result": preview,
                                }
                                yield f"data: {json.dumps(payload, default=str)}\n\n"

                elif isinstance(msg, ResultMessage):
                    if not got_content and msg.result:
                        yield f"data: {json.dumps({'type': 'text', 'text': msg.result})}\n\n"
                    input_tokens, output_tokens, cache_read = _extract_usage(msg)
                    yield f"data: {json.dumps({'type': 'usage', 'mode': req.mode, 'total_cost_usd': getattr(msg, 'total_cost_usd', 0) or 0, 'duration_ms': getattr(msg, 'duration_ms', 0) or 0, 'tool_calls': tool_calls, 'num_turns': getattr(msg, 'num_turns', 0) or 0, 'input_tokens': input_tokens, 'output_tokens': output_tokens, 'cache_read_tokens': cache_read})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'text', 'text': f'Error: {str(e)}'})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
