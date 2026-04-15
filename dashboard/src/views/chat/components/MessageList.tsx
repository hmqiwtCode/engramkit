"use client";

import { useEffect, useRef } from "react";

import { useStreamingBubble } from "../hooks/useStreamingBubble";
import type { ChatMode, Message } from "../types";
import { EmptyState } from "./EmptyState";
import { MessageBubble } from "./MessageBubble";
import { StreamingBubble } from "./StreamingBubble";

interface MessageListProps {
  messages: Message[];
  mode: ChatMode;
  streaming: boolean;
}

export function MessageList({ messages, mode, streaming }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  // Subscribe to streaming state here so the end-sentinel can scroll on every
  // live segment update — the MessageBubble children stay memo'd and don't
  // re-render.
  const stream = useStreamingBubble();

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, stream.segments, stream.active]);

  if (messages.length === 0 && !streaming) {
    return (
      <div className="flex-1 overflow-y-auto space-y-4 pb-4 scrollbar-thin">
        <EmptyState mode={mode} />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto space-y-4 pb-4 scrollbar-thin">
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}
      {streaming && <StreamingBubble />}
      <div ref={endRef} />
    </div>
  );
}
