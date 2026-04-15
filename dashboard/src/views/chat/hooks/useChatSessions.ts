"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { ChatSession, Message } from "../types";
import {
  MESSAGE_CAP_PER_SESSION,
  generateId,
  loadSessions,
  saveSessions,
} from "../lib/storage";

interface UseChatSessionsResult {
  sessions: ChatSession[];
  activeId: string;
  activeSession: ChatSession | undefined;
  hydrated: boolean;

  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;

  createSession: () => void;
  switchSession: (id: string) => void;
  deleteSession: (id: string) => void;
}

/**
 * SSR-safe session store: starts empty (matches prerender), loads localStorage
 * on mount, then keeps storage in sync. Messages live in their own state so
 * streaming updates don't thrash session serialisation on every chunk.
 */
export function useChatSessions(isStreaming: boolean): UseChatSessionsResult {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeId, setActiveId] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [hydrated, setHydrated] = useState(false);

  // Hydrate from localStorage once, post-mount.
  useEffect(() => {
    const loaded = loadSessions();
    if (loaded.length > 0) {
      const last = loaded[loaded.length - 1];
      setSessions(loaded);
      setActiveId(last.id);
      setMessages(last.messages ?? []);
    }
    setHydrated(true);
  }, []);

  // Persist the active session's messages once streaming settles.
  const lastPersistedRef = useRef<string>("");
  useEffect(() => {
    if (!hydrated || isStreaming || !activeId || messages.length === 0) return;
    const signature = `${activeId}:${messages.length}:${messages[messages.length - 1]?.content?.length ?? 0}`;
    if (signature === lastPersistedRef.current) return;
    lastPersistedRef.current = signature;

    setSessions((prev) => {
      const next = prev.map((s) =>
        s.id === activeId
          ? {
              ...s,
              messages: messages.slice(-MESSAGE_CAP_PER_SESSION),
              title: messages[0]?.content?.slice(0, 40) || s.title || "New Chat",
              updatedAt: new Date().toISOString(),
            }
          : s,
      );
      saveSessions(next);
      return next;
    });
  }, [messages, isStreaming, activeId, hydrated]);

  const activeSession = useMemo(
    () => sessions.find((s) => s.id === activeId),
    [sessions, activeId],
  );

  const createSession = useCallback(() => {
    const now = new Date().toISOString();
    const session: ChatSession = {
      id: generateId(),
      title: "New Chat",
      messages: [],
      createdAt: now,
      updatedAt: now,
    };
    setSessions((prev) => {
      const next = [...prev, session];
      saveSessions(next);
      return next;
    });
    setActiveId(session.id);
    setMessages([]);
  }, []);

  const switchSession = useCallback(
    (id: string) => {
      setSessions((prev) => {
        if (!activeId) return prev;
        const next = prev.map((s) =>
          s.id === activeId
            ? { ...s, messages: messages.slice(-MESSAGE_CAP_PER_SESSION), updatedAt: new Date().toISOString() }
            : s,
        );
        saveSessions(next);
        return next;
      });
      const target = sessions.find((s) => s.id === id);
      setActiveId(id);
      setMessages(target?.messages ?? []);
    },
    [activeId, messages, sessions],
  );

  const deleteSession = useCallback(
    (id: string) => {
      setSessions((prev) => {
        const next = prev.filter((s) => s.id !== id);
        saveSessions(next);

        if (id === activeId) {
          if (next.length > 0) {
            const last = next[next.length - 1];
            setActiveId(last.id);
            setMessages(last.messages ?? []);
          } else {
            setActiveId("");
            setMessages([]);
          }
        }
        return next;
      });
    },
    [activeId],
  );

  return {
    sessions,
    activeId,
    activeSession,
    hydrated,
    messages,
    setMessages,
    createSession,
    switchSession,
    deleteSession,
  };
}
