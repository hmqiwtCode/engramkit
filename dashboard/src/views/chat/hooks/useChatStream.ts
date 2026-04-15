"use client";

import { useCallback, useRef, useState } from "react";

import { streamStore } from "../lib/streamStore";
import type { Message, SendChatArgs, Source, ToolCall, Usage } from "../types";

interface UseChatStreamArgs {
  /** Called once per turn with the user-input message (so it can be committed immediately). */
  onUserMessage: (message: Message) => void;
  /** Called once on stream end with the fully-assembled assistant message. */
  onAssistantCommit: (message: Message) => void;
}

interface UseChatStreamResult {
  streaming: boolean;
  send: (args: SendChatArgs) => Promise<void>;
  stop: () => void;
}

// Mirrors lib/api.ts so `fetch("/api/chat")` doesn't hit the dashboard origin
// (which routes it through the SPA catch-all and 500s).
const API_BASE = process.env.NEXT_PUBLIC_ENGRAMKIT_API_URL || "";

/**
 * Runs the SSE /api/chat stream.
 *
 * All in-flight state lives in `streamStore` — committed message state is
 * touched exactly twice per turn: once to append the user message, once to
 * commit the final assistant message. The streaming bubble subscribes to the
 * store so per-chunk updates don't invalidate the committed list.
 */
export function useChatStream({
  onUserMessage,
  onAssistantCommit,
}: UseChatStreamArgs): UseChatStreamResult {
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (args: SendChatArgs) => {
      onUserMessage({ role: "user", content: args.message });
      streamStore.start();

      setStreaming(true);
      const controller = new AbortController();
      abortRef.current = controller;
      let aborted = false;

      try {
        const res = await fetch(`${API_BASE}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(args),
          signal: controller.signal,
        });

        if (!res.ok) {
          const text = await res.text();
          streamStore.pushText(`Error: ${res.status} — ${text}`);
          return;
        }

        const reader = res.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const raw = line.slice(6).trim();
            if (!raw || raw === "[DONE]") continue;

            try {
              handleEvent(JSON.parse(raw) as Record<string, unknown>);
            } catch {
              // skip malformed envelopes silently
            }
          }
        }
      } catch (err) {
        const name = (err as Error).name;
        if (name === "AbortError") {
          aborted = true;
          streamStore.markAbort();
        } else {
          streamStore.pushText(`\n\nError: ${(err as Error).message ?? "stream failed"}`);
        }
      } finally {
        if (aborted) streamStore.markAbort();
        const finalMessage = await streamStore.finalise();
        if (finalMessage) onAssistantCommit(finalMessage);
        setStreaming(false);
        abortRef.current = null;
      }
    },
    [onAssistantCommit, onUserMessage],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { streaming, send, stop };
}

/** SSE event handler — touches the store only, never React state. */
function handleEvent(data: Record<string, unknown>) {
  const type = data.type as string | undefined;
  if (!type) return;

  switch (type) {
    case "text": {
      const text = (data.content ?? data.text ?? "") as string;
      streamStore.pushText(text);
      return;
    }

    case "mode": {
      if (typeof data.mode === "string") streamStore.setMode(data.mode);
      return;
    }

    case "sources": {
      const raw = (data.sources ?? data.results ?? []) as Record<string, unknown>[];
      const srcs: Source[] = raw.map((s) => ({
        file: (s.file ?? s.file_path ?? "") as string,
        score: (s.score ?? 0) as number,
        content: s.content as string | undefined,
        wing: s.wing as string | undefined,
        room: s.room as string | undefined,
        content_hash: s.content_hash as string | undefined,
      }));
      streamStore.setSources(srcs);
      return;
    }

    case "tool_call": {
      const call: ToolCall = {
        name: (data.tool ?? data.name ?? "tool") as string,
        fullName: (data.full_name ?? data.tool ?? data.name) as string | undefined,
        input: data.input as Record<string, unknown> | undefined,
        isEngramkit: Boolean(data.is_engramkit),
      };
      const idx = (data.index ?? -1) as number;
      streamStore.pushToolCall(call, idx);
      return;
    }

    case "tool_result": {
      const idx = typeof data.index === "number" ? (data.index as number) : -1;
      const result = typeof data.result === "string" ? (data.result as string) : "";
      const isError = Boolean(data.is_error);
      streamStore.updateToolResult(idx, result, isError);
      return;
    }

    case "usage": {
      const usage: Usage = {
        total_cost_usd: (data.total_cost_usd ?? 0) as number,
        duration_ms: (data.duration_ms ?? 0) as number,
        tool_calls: (data.tool_calls ?? 0) as number,
        num_turns: (data.num_turns ?? 1) as number,
        input_tokens: (data.input_tokens ?? 0) as number,
        output_tokens: (data.output_tokens ?? 0) as number,
        cache_read_tokens: (data.cache_read_tokens ?? 0) as number,
        mode: data.mode as string | undefined,
      };
      streamStore.setUsage(usage);
      return;
    }

    case "done":
    default:
      return;
  }
}
