"use client";

import { useMemo } from "react";

import { tryParseJson } from "../lib/parseToolResult";
import type { BubbleSegment, Citation, Source, ToolCall } from "../types";

interface BuildArgs {
  sources?: Source[];
  segments?: BubbleSegment[];
  /** Legacy: for committed messages without segments but with flat toolCalls. */
  toolCalls?: ToolCall[];
}

/** Build a deduped, 1-indexed citation registry for a single assistant message.
 *  Order: RAG seed sources first (so `[^1]` tracks the user's mental model),
 *  then any new chunks surfaced by engramkit_search / engramkit_recall tool
 *  calls, in the order the tools fired. Deduped by content_hash (falling back
 *  to file+content when hash is absent). */
export function useCitationRegistry({ sources, segments, toolCalls }: BuildArgs): Citation[] {
  return useMemo(() => build({ sources, segments, toolCalls }), [sources, segments, toolCalls]);
}

/** Pure builder — exported for tests / non-React callers. */
export function buildCitationRegistry(args: BuildArgs): Citation[] {
  return build(args);
}

function build({ sources, segments, toolCalls }: BuildArgs): Citation[] {
  const out: Citation[] = [];
  const seen = new Set<string>();
  let n = 1;

  const add = (c: Omit<Citation, "index">) => {
    const key =
      c.content_hash ??
      `${c.file}::${(c.content ?? "").slice(0, 120)}`;
    if (seen.has(key)) return;
    seen.add(key);
    out.push({ ...c, index: n++ });
  };

  // 1) RAG seed sources.
  for (const s of sources ?? []) {
    if (!s?.file) continue;
    add({
      file: s.file,
      content: s.content,
      score: s.score,
      wing: s.wing,
      room: s.room,
      content_hash: s.content_hash,
      source: "seed",
    });
  }

  // 2) Tool-retrieved chunks — walk segments if present, else flat toolCalls.
  const toolCallsFromSegments = segments
    ? (segments.filter((s): s is { kind: "tool"; call: ToolCall } => s.kind === "tool").map(
        (s) => s.call,
      ) as ToolCall[])
    : [];
  const calls = segments ? toolCallsFromSegments : toolCalls ?? [];

  for (const call of calls) {
    if (!isChunkProducingTool(call.name)) continue;
    const hits = extractHits(call.result);
    for (const hit of hits) {
      add({
        file: hit.file_path ?? "?",
        content: hit.content,
        score: hit.score,
        wing: hit.wing,
        room: hit.room,
        repo: hit._repo,
        content_hash: hit.content_hash,
        source: "tool",
      });
    }
  }

  return out;
}

function isChunkProducingTool(name: string) {
  return name === "engramkit_search" || name === "engramkit_recall";
}

interface RawHit {
  file_path?: string;
  score?: number;
  content?: string;
  wing?: string;
  room?: string;
  content_hash?: string;
  _repo?: string;
}

/** Pull chunk hits out of a tool result text (JSON-encoded by the MCP server). */
function extractHits(result: string | undefined): RawHit[] {
  const parsed = tryParseJson(result);
  if (!parsed || typeof parsed !== "object") return [];
  const maybeResults = (parsed as { results?: unknown }).results;
  if (Array.isArray(maybeResults)) return maybeResults as RawHit[];
  // engramkit_recall returns { recalls: [{ repo, text }] } — no chunk structure
  // to cite individually, so we skip it for registry purposes.
  return [];
}
