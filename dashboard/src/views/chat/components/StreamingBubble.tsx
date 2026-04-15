"use client";

import { useStreamingBubble } from "../hooks/useStreamingBubble";
import { AssistantBubble } from "./MessageBubble";

/**
 * Live-updating assistant bubble. Subscribes to streamStore via
 * useSyncExternalStore so it's the ONLY component re-rendering during SSE
 * — committed MessageBubbles (wrapped in memo) stay frozen.
 */
export function StreamingBubble() {
  const state = useStreamingBubble();
  if (!state.active) return null;
  return (
    <AssistantBubble
      data={{
        segments: state.segments,
        sources: state.sources,
        usage: state.usage,
        mode: state.mode,
        streaming: true,
      }}
    />
  );
}
