"use client";

import { memo } from "react";

import { useCitationRegistry } from "../hooks/useCitationRegistry";
import type { BubbleSegment, Message, Source, ToolCall, Usage } from "../types";
import { CitationsPanel } from "./CitationsPanel";
import { SegmentView } from "./Segment";
import { ToolCallPills } from "./ToolCallPills";
import { UsageStats } from "./UsageStats";

export interface AssistantBubbleData {
  segments?: BubbleSegment[];
  /** Legacy text body — used only if `segments` is absent. */
  content?: string;
  toolCalls?: ToolCall[];
  sources?: Source[];
  usage?: Usage;
  mode?: string;
  /** True when this is the live streaming bubble (shows cursor on trailing text). */
  streaming?: boolean;
}

/* ────────────────── Public API ────────────────── */

/** Memo'd committed-message bubble. Takes a frozen Message — never mutates
 *  during streaming, so the list doesn't re-render on SSE chunks. */
export const MessageBubble = memo(function MessageBubble({ message }: { message: Message }) {
  if (message.role === "user") return <UserBubble content={message.content} />;
  return (
    <AssistantBubble
      data={{
        segments: message.segments,
        content: message.content,
        toolCalls: message.toolCalls,
        sources: message.sources,
        usage: message.usage,
        mode: message.usage?.mode,
        streaming: false,
      }}
    />
  );
});

/** Shared assistant-bubble shell. Used by both committed MessageBubble and
 *  the live StreamingBubble so visual parity is automatic. */
export function AssistantBubble({ data }: { data: AssistantBubbleData }) {
  const citations = useCitationRegistry({
    sources: data.sources,
    segments: data.segments,
    toolCalls: data.toolCalls,
  });

  return (
    <div className="flex justify-start">
      <div className="max-w-[80%] bg-[#111] border border-white/[0.06] rounded-2xl rounded-bl-md px-5 py-4">
        <AssistantBody data={data} citations={citations} />

        {data.mode && <ModeBadge mode={data.mode} />}

        {/* Legacy fallback: old sessions have toolCalls but no segments. */}
        {!data.segments && data.toolCalls && data.toolCalls.length > 0 && (
          <ToolCallPills toolCalls={data.toolCalls} streaming={Boolean(data.streaming)} />
        )}

        {citations.length > 0 && <CitationsPanel citations={citations} />}

        {data.usage && <UsageStats usage={data.usage} />}
      </div>
    </div>
  );
}

/* ────────────────── Internals ────────────────── */

function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] bg-blue-500/10 border border-blue-500/20 rounded-2xl rounded-br-md px-4 py-3">
        <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">{content}</p>
      </div>
    </div>
  );
}

function AssistantBody({
  data,
  citations,
}: {
  data: AssistantBubbleData;
  citations: ReturnType<typeof useCitationRegistry>;
}) {
  // Modern path: render the interleaved timeline.
  if (data.segments && data.segments.length > 0) {
    const lastIdx = data.segments.length - 1;
    return (
      <div className="space-y-1.5">
        {data.segments.map((seg, i) => (
          <SegmentView
            key={i}
            segment={seg}
            citations={citations}
            isStreamingTail={Boolean(data.streaming) && i === lastIdx && seg.kind === "text"}
          />
        ))}
      </div>
    );
  }

  // Streaming but not yet any segment — show the three-dot pulse.
  if (data.streaming && !data.content) return <BouncingDots />;

  // Legacy rendering: plain markdown content (old sessions). Still pass
  // citations so raw file paths in legacy messages also get linked.
  if (data.content) {
    return (
      <SegmentView
        segment={{ kind: "text", content: data.content }}
        citations={citations}
        isStreamingTail={false}
      />
    );
  }

  return null;
}

function BouncingDots() {
  return (
    <span className="inline-flex gap-1">
      <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
      <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse [animation-delay:150ms]" />
      <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse [animation-delay:300ms]" />
    </span>
  );
}

function ModeBadge({ mode }: { mode: string }) {
  const rag = mode.toLowerCase() === "rag";
  return (
    <div className="mt-2">
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono font-medium ${
          rag
            ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
            : "bg-gray-500/10 text-gray-400 border border-gray-500/20"
        }`}
      >
        {mode.toUpperCase()}
      </span>
    </div>
  );
}
