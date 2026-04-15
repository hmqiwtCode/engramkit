"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ChatInput } from "./components/ChatInput";
import { ChatToolbar } from "./components/ChatToolbar";
import { MessageList } from "./components/MessageList";
import { SessionsSidebar } from "./components/SessionsSidebar";
import { useChatSessions } from "./hooks/useChatSessions";
import { useChatStream } from "./hooks/useChatStream";
import { useVaults } from "./hooks/useVaults";
import type { ChatMode, Message } from "./types";

/**
 * Top-level chat view.
 *
 * Design:
 *   - Committed message list in `useChatSessions` (memo'd bubbles, never
 *     mutates during streaming).
 *   - In-flight assistant bubble in `streamStore` — only the `StreamingBubble`
 *     subscribes, so per-chunk updates skip the committed list entirely.
 *   - On send: append user message once. On end: append final assistant
 *     message once. Two state updates per turn, not 200+.
 */
export default function ChatPage() {
  const [streaming, setStreaming] = useState(false);

  const sessions = useChatSessions(streaming);
  const { vaults } = useVaults();

  const [chatMode, setChatMode] = useState<ChatMode>("rag");
  const [nContext, setNContext] = useState(10);
  const [selectedVaults, setSelectedVaults] = useState<string[]>([]);

  useEffect(() => {
    if (vaults.length > 0 && selectedVaults.length === 0) {
      setSelectedVaults([vaults[0].vault_id]);
    }
  }, [vaults, selectedVaults.length]);

  const [input, setInput] = useState("");
  const [showSessions, setShowSessions] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (sessions.hydrated && sessions.sessions.length === 0) {
      sessions.createSession();
    }
  }, [sessions]);

  const appendUser = useCallback(
    (msg: Message) => {
      sessions.setMessages((prev) => [...prev, msg]);
    },
    [sessions],
  );

  const appendAssistantCommit = useCallback(
    (msg: Message) => {
      sessions.setMessages((prev) => [...prev, msg]);
    },
    [sessions],
  );

  const stream = useChatStream({
    onUserMessage: appendUser,
    onAssistantCommit: appendAssistantCommit,
  });

  useEffect(() => setStreaming(stream.streaming), [stream.streaming]);

  const handleSubmit = useCallback(() => {
    const query = input.trim();
    if (!query || stream.streaming) return;
    setInput("");

    const history = sessions.messages.slice(-10).map((m) => ({
      role: m.role,
      content: m.content,
    }));
    stream.send({
      message: query,
      mode: chatMode,
      vault_ids: selectedVaults,
      n_context: nContext,
      history,
    });
  }, [chatMode, input, nContext, selectedVaults, sessions.messages, stream]);

  useEffect(() => {
    if (!stream.streaming) inputRef.current?.focus();
  }, [stream.streaming]);

  const handleClear = useCallback(() => {
    sessions.createSession();
  }, [sessions]);

  const toggleVault = useCallback((id: string) => {
    setSelectedVaults((prev) => (prev.includes(id) ? prev.filter((v) => v !== id) : [...prev, id]));
  }, []);

  return (
    <div className="flex h-[calc(100vh-64px)] bg-[#0a0a0a]">
      {showSessions && (
        <SessionsSidebar
          sessions={sessions.sessions}
          activeId={sessions.activeId}
          onCreate={sessions.createSession}
          onSwitch={sessions.switchSession}
          onDelete={sessions.deleteSession}
        />
      )}

      <div className="flex-1 flex flex-col min-w-0">
        <ChatToolbar
          showSessions={showSessions}
          onToggleSessions={() => setShowSessions((v) => !v)}
          vaults={vaults}
          selectedVaults={selectedVaults}
          onToggleVault={toggleVault}
          onClearVaults={() => setSelectedVaults([])}
          mode={chatMode}
          onSetMode={setChatMode}
          nContext={nContext}
          onSetNContext={setNContext}
          canClear={sessions.hydrated && sessions.messages.length > 0}
          onClear={handleClear}
        />

        <MessageList messages={sessions.messages} mode={chatMode} streaming={stream.streaming} />

        <ChatInput
          ref={inputRef}
          value={input}
          onChange={setInput}
          onSubmit={handleSubmit}
          onStop={stream.stop}
          streaming={stream.streaming}
          mode={chatMode}
        />
      </div>
    </div>
  );
}
