"use client";

import { useSyncExternalStore } from "react";

import { streamStore, type StreamState } from "../lib/streamStore";

/** Subscribe to the in-flight streaming bubble. Only components that actually
 *  need live state should call this — anything wrapped in memo around the
 *  committed message list must not. */
export function useStreamingBubble(): StreamState {
  return useSyncExternalStore(
    streamStore.subscribe,
    streamStore.getSnapshot,
    streamStore.getServerSnapshot,
  );
}
