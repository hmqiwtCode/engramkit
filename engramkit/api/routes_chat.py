"""RAG chat endpoint — search vault + stream via Claude Agent SDK."""

import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from engramkit.search.hybrid import hybrid_search
from engramkit.api.helpers import get_vault_by_id, ChatRequest

router = APIRouter(prefix="/api", tags=["chat"])


def _format_history(history: list) -> str:
    """Format conversation history for the prompt."""
    if not history:
        return ""
    lines = ["## Conversation History:"]
    for h in history[-10:]:  # last 10 messages
        role = h.get("role", "user")
        content = h.get("content", "")[:500]  # truncate long messages
        lines.append(f"**{role}:** {content}")
    lines.append("")
    return "\n".join(lines) + "\n"


def _extract_usage(msg):
    """Extract token counts from ResultMessage."""
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


@router.post("/chat")
async def chat(req: ChatRequest):
    from claude_agent_sdk import (
        query as sdk_query, ClaudeAgentOptions,
        AssistantMessage, TextBlock, ToolUseBlock, ResultMessage, StreamEvent,
    )

    # 1. Resolve vault IDs + repo paths
    vault_ids = req.vault_ids or ([req.vault_id] if req.vault_id else [])
    if not vault_ids:
        raise HTTPException(400, "No vault selected")

    repo_names = []
    repo_paths = []
    for vid in vault_ids:
        vault = get_vault_by_id(vid)
        try:
            rp = vault.get_meta("repo_path", "unknown")
            repo_names.append(rp.split("/")[-1] if rp else vid)
            if rp: repo_paths.append(rp)
        finally:
            vault.close()

    repo_name = ", ".join(repo_names)

    # 2. Build prompt based on mode
    results = []
    if req.mode == "rag":
        # Search across vaults
        for vid in vault_ids:
            vault = get_vault_by_id(vid)
            try:
                hits = hybrid_search(req.message, vault, n_results=req.n_context)
                rp = vault.get_meta("repo_path", "unknown")
                rn = rp.split("/")[-1] if rp else vid
                for r in hits: r["_repo"] = rn
                results.extend(hits)
            finally:
                vault.close()

        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        results = results[:req.n_context]

        context_chunks = [
            f"[{r.get('_repo', '')}/{r['file_path']}] (score: {r['score']:.4f})\n{r['content']}"
            for r in results
        ]
        context = "\n\n---\n\n".join(context_chunks) if context_chunks else "No relevant context."

        pinned = ""
        if req.pinned_chunks:
            pinned = "\n\n---\n\n".join(f"[{pc.get('file','?')}] (pinned)\n{pc.get('content','')}" for pc in req.pinned_chunks)

        full_context = f"## Pinned:\n{pinned}\n\n## Auto-Retrieved:\n{context}" if pinned else context

        prompt = f"""You are a code assistant for the "{repo_name}" codebase.

RULES:
1. Answer PRIMARILY from the pre-searched code chunks below
2. Only use Read/Grep if chunks clearly don't contain the answer (max 2-3 tool calls)
3. Do NOT explore the entire codebase — be focused
4. Reference specific file paths
5. Be concise

## Pre-Searched Code Chunks:
{full_context}

{_format_history(req.history)}## Question:
{req.message}"""

    else:
        # Direct mode — no RAG, just Claude + tools
        prompt = f"""You are a code assistant for the "{repo_name}" codebase.

Answer the question using your tools (Read, Grep, Glob). Be concise.

{_format_history(req.history)}## Question:
{req.message}"""

    # 3. Stream response
    async def generate():
        # Send mode indicator
        yield f"data: {json.dumps({'type': 'mode', 'mode': req.mode})}\n\n"

        # Send sources (only in RAG mode)
        if results:
            sources = [{
                "file": r.get("file_path", "?"), "score": r.get("score", 0),
                "content": r.get("content", ""), "wing": r.get("wing", ""),
                "room": r.get("room", ""), "content_hash": r.get("content_hash", ""),
            } for r in results]
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

        got_content = False
        tool_calls = 0

        try:
            async for msg in sdk_query(
                prompt=prompt,
                options=ClaudeAgentOptions(
                    max_turns=None,
                    permission_mode="auto",
                    model=req.model or None,
                    include_partial_messages=True,
                    cwd=repo_paths[0] if repo_paths else None,
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
                            yield f"data: {json.dumps({'type': 'tool_call', 'tool': block.name, 'count': tool_calls})}\n\n"
                        elif isinstance(block, TextBlock) and block.text and not got_content:
                            got_content = True
                            yield f"data: {json.dumps({'type': 'text', 'text': block.text})}\n\n"

                elif isinstance(msg, ResultMessage):
                    if not got_content and msg.result:
                        yield f"data: {json.dumps({'type': 'text', 'text': msg.result})}\n\n"
                    input_tokens, output_tokens, cache_read = _extract_usage(msg)
                    yield f"data: {json.dumps({'type': 'usage', 'mode': req.mode, 'total_cost_usd': getattr(msg, 'total_cost_usd', 0) or 0, 'duration_ms': getattr(msg, 'duration_ms', 0) or 0, 'tool_calls': tool_calls, 'num_turns': getattr(msg, 'num_turns', 0) or 0, 'input_tokens': input_tokens, 'output_tokens': output_tokens, 'cache_read_tokens': cache_read})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'text', 'text': f'Error: {str(e)}'})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
