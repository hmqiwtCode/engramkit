"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { vaults as vaultsApi } from "@/lib/api";
import { Badge } from "@/components/shared/badge";
import type { VaultSummary } from "@/lib/types";

/* ─── Types ───────────────────────────────────────────────────────── */

interface Source {
  file: string;
  score: number;
  content?: string;
  wing?: string;
  room?: string;
  content_hash?: string;
}

interface Usage {
  total_cost_usd: number;
  duration_ms: number;
  tool_calls: number;
  num_turns: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  mode?: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  toolCalls?: string[];
  usage?: Usage;
}

type ChatMode = "rag" | "direct";

/* ─── Typewriter hook ─────────────────────────────────────────────── */

function useTypewriter(rate = 200) {
  const bufferRef = useRef("");
  const displayRef = useRef("");
  const rafRef = useRef<number>(0);
  const lastRef = useRef<number>(0);
  const [displayed, setDisplayed] = useState("");

  const push = useCallback((text: string) => {
    bufferRef.current += text;
    if (rafRef.current) return; // already ticking

    const tick = (now: number) => {
      if (!lastRef.current) lastRef.current = now;
      const elapsed = now - lastRef.current;
      const chars = Math.max(1, Math.floor((elapsed / 1000) * rate));
      lastRef.current = now;

      if (bufferRef.current.length > 0) {
        const take = Math.min(chars, bufferRef.current.length);
        displayRef.current += bufferRef.current.slice(0, take);
        bufferRef.current = bufferRef.current.slice(take);
        setDisplayed(displayRef.current);
      }

      if (bufferRef.current.length > 0) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        rafRef.current = 0;
      }
    };

    rafRef.current = requestAnimationFrame(tick);
  }, [rate]);

  const flush = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = 0;
    }
    displayRef.current += bufferRef.current;
    bufferRef.current = "";
    setDisplayed(displayRef.current);
  }, []);

  const reset = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = 0;
    }
    bufferRef.current = "";
    displayRef.current = "";
    lastRef.current = 0;
    setDisplayed("");
  }, []);

  useEffect(() => {
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return { displayed, push, flush, reset };
}

/* ─── Component ───────────────────────────────────────────────────── */

interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
}

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
}

function loadSessions(): ChatSession[] {
  if (typeof window === "undefined") return [];
  try {
    const saved = localStorage.getItem("engramkit_chat_sessions");
    return saved ? JSON.parse(saved) : [];
  } catch { return []; }
}

function saveSessions(sessions: ChatSession[]) {
  try { localStorage.setItem("engramkit_chat_sessions", JSON.stringify(sessions.slice(-20))); } catch {}
}

export default function ChatPage() {
  /* ── Session management ── */
  const [sessions, setSessions] = useState<ChatSession[]>(loadSessions);
  const [activeSessionId, setActiveSessionId] = useState<string>(() => {
    const s = loadSessions();
    return s.length > 0 ? s[s.length - 1].id : "";
  });
  const [showSessions, setShowSessions] = useState(false);

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  /* ── Vault state ── */
  const [vaultList, setVaultList] = useState<VaultSummary[]>([]);
  const [selectedVaults, setSelectedVaults] = useState<string[]>([]);
  const [showVaultDropdown, setShowVaultDropdown] = useState(false);

  /* ── Chat config ── */
  const [chatMode, setChatMode] = useState<ChatMode>("rag");
  const [nContext, setNContext] = useState(10);

  /* ── Messages ── */
  const [messages, setMessages] = useState<Message[]>(activeSession?.messages || []);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);

  /* ── Source reference panel ── */
  const [expandedMsgIdx, setExpandedMsgIdx] = useState<number | null>(null);
  const [expandedSourceIdx, setExpandedSourceIdx] = useState<number | null>(null);

  /* ── Session helpers ── */
  const createNewSession = () => {
    const session: ChatSession = {
      id: generateId(),
      title: "New Chat",
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    const updated = [...sessions, session];
    setSessions(updated);
    saveSessions(updated);
    setActiveSessionId(session.id);
    setMessages([]);
    setExpandedMsgIdx(null);
    setExpandedSourceIdx(null);
  };

  const switchSession = (id: string) => {
    // Save current session first
    if (activeSessionId) {
      const updated = sessions.map((s) =>
        s.id === activeSessionId ? { ...s, messages, updatedAt: new Date().toISOString() } : s
      );
      setSessions(updated);
      saveSessions(updated);
    }
    // Load target session
    const target = sessions.find((s) => s.id === id);
    setActiveSessionId(id);
    setMessages(target?.messages || []);
    setExpandedMsgIdx(null);
    setExpandedSourceIdx(null);
    setShowSessions(false);
  };

  const deleteSession = (id: string) => {
    const updated = sessions.filter((s) => s.id !== id);
    setSessions(updated);
    saveSessions(updated);
    if (id === activeSessionId) {
      if (updated.length > 0) {
        switchSession(updated[updated.length - 1].id);
      } else {
        setActiveSessionId("");
        setMessages([]);
      }
    }
  };

  /* ── Refs ── */
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  /* ── Typewriter ── */
  const typewriter = useTypewriter(200);

  /* ── Streaming accumulators (ref so we don't re-render per SSE line) ── */
  const streamContentRef = useRef("");
  const streamSourcesRef = useRef<Source[]>([]);
  const streamToolsRef = useRef<string[]>([]);
  const streamUsageRef = useRef<Usage | undefined>(undefined);

  /* ── Persist messages to sessions ── */
  useEffect(() => {
    if (!streaming && activeSessionId && messages.length > 0) {
      const title = messages[0]?.content?.slice(0, 40) || "New Chat";
      const updated = sessions.map((s) =>
        s.id === activeSessionId
          ? { ...s, messages: messages.slice(-50), title, updatedAt: new Date().toISOString() }
          : s
      );
      setSessions(updated);
      saveSessions(updated);
    }
  }, [messages, streaming]);

  /* ── Fetch vault list ── */
  useEffect(() => {
    vaultsApi.list().then((list) => {
      setVaultList(list);
      if (list.length > 0) {
        setSelectedVaults([list[0].vault_id]);
      }
    }).catch(() => {});
  }, []);

  /* ── Auto-scroll ── */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typewriter.displayed]);

  /* ── Close vault dropdown on outside click ── */
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowVaultDropdown(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  /* ── Toggle vault selection ── */
  const toggleVault = (id: string) => {
    setSelectedVaults((prev) =>
      prev.includes(id) ? prev.filter((v) => v !== id) : [...prev, id]
    );
  };

  /* ── Stop streaming ── */
  const handleStop = () => {
    abortRef.current?.abort();
  };

  /* ── Clear chat (starts new session) ── */
  const handleClear = () => {
    createNewSession();
    typewriter.reset();
  };

  /* ── Send message ── */
  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    const query = input.trim();
    if (!query || streaming) return;

    setInput("");
    setExpandedMsgIdx(null);
    setExpandedSourceIdx(null);

    const userMsg: Message = { role: "user", content: query };
    setMessages((prev) => [...prev, userMsg]);

    // Reset streaming accumulators
    streamContentRef.current = "";
    streamSourcesRef.current = [];
    streamToolsRef.current = [];
    streamUsageRef.current = undefined;
    typewriter.reset();

    // Add placeholder assistant message
    const assistantMsg: Message = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, assistantMsg]);
    setStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: query,
          mode: chatMode,
          vault_ids: selectedVaults,
          n_context: nContext,
          history: messages.slice(-10).map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const text = await res.text();
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            content: `Error: ${res.status} — ${text}`,
          };
          return updated;
        });
        setStreaming(false);
        return;
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let sseBuffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        sseBuffer += decoder.decode(value, { stream: true });
        const lines = sseBuffer.split("\n");
        sseBuffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (!raw || raw === "[DONE]") continue;

          let data: any;
          try {
            data = JSON.parse(raw);
          } catch {
            continue;
          }

          switch (data.type) {
            case "text": {
              streamContentRef.current += data.content ?? data.text ?? "";
              typewriter.push(data.content ?? data.text ?? "");
              break;
            }

            case "sources": {
              const srcs: Source[] = (data.sources ?? data.results ?? []).map((s: any) => ({
                file: s.file ?? s.file_path ?? "",
                score: s.score ?? 0,
                content: s.content,
                wing: s.wing,
                room: s.room,
                content_hash: s.content_hash,
              }));
              streamSourcesRef.current = srcs;
              // Immediately reflect sources on the message
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  sources: srcs,
                };
                return updated;
              });
              break;
            }

            case "tool_call": {
              const name = data.name ?? data.tool ?? "tool";
              streamToolsRef.current = [...streamToolsRef.current, name];
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  toolCalls: [...streamToolsRef.current],
                };
                return updated;
              });
              break;
            }

            case "usage": {
              const u: Usage = {
                total_cost_usd: data.total_cost_usd ?? 0,
                duration_ms: data.duration_ms ?? 0,
                tool_calls: data.tool_calls ?? 0,
                num_turns: data.num_turns ?? 1,
                input_tokens: data.input_tokens ?? 0,
                output_tokens: data.output_tokens ?? 0,
                cache_read_tokens: data.cache_read_tokens ?? 0,
                mode: data.mode,
              };
              streamUsageRef.current = u;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  usage: u,
                };
                return updated;
              });
              break;
            }

            case "mode": {
              // Mode info is also included in usage event — skip here
              break;
            }

            case "done": {
              // Stream finished
              break;
            }
          }
        }
      }

      // Flush typewriter buffer and finalize message
      typewriter.flush();
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          content: streamContentRef.current,
          sources: streamSourcesRef.current.length > 0 ? streamSourcesRef.current : undefined,
          toolCalls: streamToolsRef.current.length > 0 ? streamToolsRef.current : undefined,
          usage: streamUsageRef.current,
        };
        return updated;
      });
    } catch (err: any) {
      if (err.name !== "AbortError") {
        typewriter.flush();
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            content: streamContentRef.current || `Error: ${err.message}`,
          };
          return updated;
        });
      } else {
        // Aborted — commit whatever we have
        typewriter.flush();
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            content: streamContentRef.current,
            sources: streamSourcesRef.current.length > 0 ? streamSourcesRef.current : undefined,
            toolCalls: streamToolsRef.current.length > 0 ? streamToolsRef.current : undefined,
            usage: streamUsageRef.current,
          };
          return updated;
        });
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
      inputRef.current?.focus();
    }
  }, [input, streaming, chatMode, selectedVaults, nContext, typewriter]);

  /* ── Determine assistant display text (typewriter while streaming) ── */
  const getAssistantContent = (msg: Message, idx: number): string => {
    if (streaming && idx === messages.length - 1) {
      return typewriter.displayed;
    }
    return msg.content;
  };

  /* ────────────────── RENDER ────────────────── */

  // Auto-create first session if none
  useEffect(() => {
    if (sessions.length === 0) createNewSession();
  }, []);

  return (
    <div className="flex h-[calc(100vh-64px)] bg-[#0a0a0a]">
      {/* ─── Sessions sidebar ─── */}
      {showSessions && (
        <div className="w-64 flex-shrink-0 border-r border-white/[0.06] flex flex-col bg-[#0c0c0c]">
          <div className="flex items-center justify-between px-3 py-3 border-b border-white/[0.06]">
            <span className="text-[11px] text-gray-500 uppercase tracking-wider font-medium">Chat History</span>
            <button
              onClick={createNewSession}
              className="text-xs text-blue-400 hover:text-blue-300 font-medium transition-colors"
            >+ New</button>
          </div>
          <div className="flex-1 overflow-y-auto py-1">
            {[...sessions].reverse().map((s) => (
              <div
                key={s.id}
                className={`group flex items-center gap-2 px-3 py-2.5 cursor-pointer transition-colors ${
                  s.id === activeSessionId ? "bg-white/[0.04] text-gray-200" : "text-gray-500 hover:bg-white/[0.02] hover:text-gray-300"
                }`}
              >
                <div className="flex-1 min-w-0" onClick={() => switchSession(s.id)}>
                  <p className="text-xs truncate">{s.title || "New Chat"}</p>
                  <p className="text-[10px] text-gray-600 mt-0.5">
                    {s.messages.length} msgs · {new Date(s.updatedAt).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); deleteSession(s.id); }}
                  className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-red-400 transition-all p-1"
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ─── Main chat area ─── */}
      <div className="flex-1 flex flex-col min-w-0">
      {/* ─── Header bar ─── */}
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-white/[0.06] px-1">
        <div className="flex items-center gap-3">
          {/* Toggle sessions panel */}
          <button
            onClick={() => setShowSessions(!showSessions)}
            className={`p-2 rounded-lg transition-colors ${showSessions ? "bg-blue-600 text-white" : "bg-[#111] text-gray-500 hover:text-gray-300 border border-white/[0.06]"}`}
            title="Chat history"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12" />
            </svg>
          </button>
          {/* Vault multi-select */}
          <div ref={dropdownRef} className="relative">
            <button
              onClick={() => setShowVaultDropdown(!showVaultDropdown)}
              className="flex items-center gap-2 bg-[#111] border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 font-mono hover:border-white/[0.12] transition-colors"
            >
              <svg className="w-3.5 h-3.5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375" />
              </svg>
              {selectedVaults.length === 0
                ? "All vaults"
                : selectedVaults.length === 1
                  ? vaultList.find((v) => v.vault_id === selectedVaults[0])?.repo_path?.split("/").pop() ?? selectedVaults[0]
                  : `${selectedVaults.length} vaults`}
              <svg className="w-3 h-3 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
              </svg>
            </button>

            {showVaultDropdown && (
              <div className="absolute top-full left-0 mt-1 w-64 bg-[#111] border border-white/[0.06] rounded-lg shadow-2xl shadow-black/50 z-50 py-1 max-h-64 overflow-y-auto">
                {/* All vaults option */}
                <button
                  onClick={() => setSelectedVaults([])}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 text-left text-sm hover:bg-white/[0.02] transition-colors ${selectedVaults.length === 0 ? "text-blue-400" : "text-gray-400"}`}
                >
                  <div className={`w-3.5 h-3.5 rounded border ${selectedVaults.length === 0 ? "bg-blue-600 border-blue-500" : "border-white/[0.12]"} flex items-center justify-center`}>
                    {selectedVaults.length === 0 && (
                      <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                      </svg>
                    )}
                  </div>
                  <span className="font-mono">All vaults</span>
                </button>
                {vaultList.map((v) => (
                  <button
                    key={v.vault_id}
                    onClick={() => toggleVault(v.vault_id)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 text-left text-sm hover:bg-white/[0.02] transition-colors ${selectedVaults.includes(v.vault_id) ? "text-blue-400" : "text-gray-400"}`}
                  >
                    <div className={`w-3.5 h-3.5 rounded border ${selectedVaults.includes(v.vault_id) ? "bg-blue-600 border-blue-500" : "border-white/[0.12]"} flex items-center justify-center`}>
                      {selectedVaults.includes(v.vault_id) && (
                        <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                        </svg>
                      )}
                    </div>
                    <span className="font-mono truncate">{v.repo_path?.split("/").pop() || v.vault_id}</span>
                    <span className="text-[10px] text-gray-600 ml-auto font-mono tabular-nums">{v.total_chunks}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Mode toggle: RAG / Direct */}
          <div className="flex items-center bg-[#111] border border-white/[0.06] rounded-lg overflow-hidden">
            <button
              onClick={() => setChatMode("rag")}
              className={`px-3 py-2 text-xs font-medium transition-colors ${chatMode === "rag" ? "bg-blue-600/20 text-blue-400 border-r border-blue-500/20" : "text-gray-500 hover:text-gray-300 border-r border-white/[0.06]"}`}
            >
              RAG
            </button>
            <button
              onClick={() => setChatMode("direct")}
              className={`px-3 py-2 text-xs font-medium transition-colors ${chatMode === "direct" ? "bg-blue-600/20 text-blue-400" : "text-gray-500 hover:text-gray-300"}`}
            >
              Direct
            </button>
          </div>

          {/* Chunks count selector (only in RAG mode) */}
          {chatMode === "rag" && (
            <div className="flex items-center gap-1.5">
              <label className="text-[10px] text-gray-600 uppercase tracking-wider">Chunks</label>
              <select
                value={nContext}
                onChange={(e) => setNContext(Number(e.target.value))}
                className="appearance-none bg-[#111] border border-white/[0.06] rounded-lg px-3 py-1.5 pr-6 text-xs text-gray-400 font-mono focus:outline-none focus:border-blue-500/50 cursor-pointer"
              >
                {[5, 10, 15, 20].map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Right: clear */}
        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              onClick={handleClear}
              className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-300 bg-gray-800 hover:bg-gray-700 border border-white/[0.06] rounded-lg transition-colors font-medium"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* ─── Messages ─── */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4 scrollbar-thin">
        {/* Empty state */}
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mb-5">
              <svg className="w-6 h-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
              </svg>
            </div>
            <p className="text-sm text-gray-300 font-medium mb-1.5">Start a conversation</p>
            <p className="text-xs text-gray-600 max-w-sm leading-relaxed">
              {chatMode === "rag"
                ? "Your message will search the knowledge base for relevant context before generating a response."
                : "Direct mode — Claude will respond without searching the knowledge base."}
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[80%] ${
                msg.role === "user"
                  ? "bg-blue-500/10 border border-blue-500/20 rounded-2xl rounded-br-md px-4 py-3"
                  : "bg-[#111] border border-white/[0.06] rounded-2xl rounded-bl-md px-5 py-4"
              }`}
            >
              {/* ── Message content ── */}
              {msg.role === "assistant" ? (
                <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-[#0a0a0a] prose-pre:border prose-pre:border-white/[0.06] prose-code:text-blue-300 prose-code:font-mono prose-headings:text-gray-100 prose-a:text-blue-400">
                  {getAssistantContent(msg, i) ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {getAssistantContent(msg, i)}
                    </ReactMarkdown>
                  ) : streaming && i === messages.length - 1 ? (
                    <span className="inline-flex gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse [animation-delay:150ms]" />
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse [animation-delay:300ms]" />
                    </span>
                  ) : null}
                  {/* Streaming cursor */}
                  {streaming && i === messages.length - 1 && getAssistantContent(msg, i) && (
                    <span className="inline-block w-0.5 h-4 bg-blue-400 animate-pulse ml-0.5 align-text-bottom" />
                  )}
                </div>
              ) : (
                <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">{msg.content}</p>
              )}

              {/* ── Mode badge ── */}
              {msg.usage?.mode && (
                <div className="mt-2">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono font-medium ${
                    msg.usage.mode.toLowerCase() === "rag"
                      ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                      : "bg-gray-500/10 text-gray-400 border border-gray-500/20"
                  }`}>
                    {msg.usage.mode.toUpperCase()}
                  </span>
                </div>
              )}

              {/* ── Tool call badges ── */}
              {msg.toolCalls && msg.toolCalls.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-white/[0.04]">
                  {msg.toolCalls.map((tool, ti) => (
                    <span
                      key={ti}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border border-amber-500/20 bg-amber-500/10 text-[10px] text-amber-400 font-mono"
                    >
                      <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17 17.25 21A2.652 2.652 0 0 0 21 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 1 1-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 0 0 4.486-6.336l-3.276 3.277a3.004 3.004 0 0 1-2.25-2.25l3.276-3.276a4.5 4.5 0 0 0-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085" />
                      </svg>
                      {tool}
                    </span>
                  ))}
                </div>
              )}

              {/* ── Source badges + reference panel ── */}
              {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-white/[0.06]">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] text-gray-600 uppercase tracking-wider">Sources</span>
                    {msg.sources.map((src, si) => (
                      <button
                        key={si}
                        onClick={() => {
                          if (expandedMsgIdx === i && expandedSourceIdx === si) {
                            setExpandedSourceIdx(null);
                            setExpandedMsgIdx(null);
                          } else {
                            setExpandedMsgIdx(i);
                            setExpandedSourceIdx(si);
                          }
                        }}
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-mono transition-colors ${
                          expandedMsgIdx === i && expandedSourceIdx === si
                            ? "bg-blue-500/15 border border-blue-500/30 text-blue-400"
                            : "bg-white/[0.04] border border-white/[0.06] text-gray-400 hover:text-gray-300 hover:border-white/[0.1]"
                        }`}
                      >
                        <span className="truncate max-w-[120px]">
                          {src.file ? src.file.split("/").pop() : `[${si + 1}]`}
                        </span>
                        <span className="text-[9px] text-gray-600">{src.score.toFixed(2)}</span>
                      </button>
                    ))}
                  </div>

                  {/* Expanded source content */}
                  {expandedMsgIdx === i && expandedSourceIdx !== null && msg.sources[expandedSourceIdx] && (
                    <div className="mt-3 bg-[#0a0a0a] border border-white/[0.04] rounded-lg overflow-hidden">
                      <div className="flex items-center justify-between px-3 py-2.5 border-b border-white/[0.04]">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="text-[10px] text-gray-600 font-mono">[{expandedSourceIdx + 1}]</span>
                          {msg.sources[expandedSourceIdx].wing && (
                            <Badge variant={msg.sources[expandedSourceIdx].wing === "semantic" ? "semantic" : msg.sources[expandedSourceIdx].wing === "lexical" ? "lexical" : "default"}>
                              {msg.sources[expandedSourceIdx].wing}
                            </Badge>
                          )}
                          {msg.sources[expandedSourceIdx].room && (
                            <Badge>{msg.sources[expandedSourceIdx].room}</Badge>
                          )}
                          <span className="text-[10px] text-blue-400/60 font-mono truncate">
                            {msg.sources[expandedSourceIdx].file}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <span className="text-[10px] text-gray-600 font-mono tabular-nums">
                            {msg.sources[expandedSourceIdx].score.toFixed(3)}
                          </span>
                          <button
                            onClick={() => { setExpandedSourceIdx(null); setExpandedMsgIdx(null); }}
                            className="text-gray-600 hover:text-gray-400 transition-colors"
                          >
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      </div>
                      {msg.sources[expandedSourceIdx].content ? (
                        <div className="px-3 pb-3">
                          <pre className="text-xs text-gray-400 leading-relaxed font-mono whitespace-pre-wrap mt-2 max-h-48 overflow-y-auto">
                            {msg.sources[expandedSourceIdx].content}
                          </pre>
                        </div>
                      ) : (
                        <div className="px-3 py-3">
                          <span className="text-xs text-gray-600 italic">No content preview available.</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* ── Usage stats ── */}
              {msg.usage && (
                <div className="flex items-center gap-3 mt-2 pt-2 border-t border-white/[0.04] flex-wrap">
                  {msg.usage.duration_ms > 0 && (
                    <span className="text-[10px] text-gray-600 font-mono tabular-nums">
                      {(msg.usage.duration_ms / 1000).toFixed(1)}s
                    </span>
                  )}
                  {msg.usage.total_cost_usd > 0 && (
                    <span className="text-[10px] text-gray-600 font-mono tabular-nums">
                      ${msg.usage.total_cost_usd.toFixed(4)}
                    </span>
                  )}
                  {(msg.usage.input_tokens > 0 || msg.usage.output_tokens > 0) && (
                    <span className="text-[10px] text-gray-600 font-mono tabular-nums">
                      {msg.usage.input_tokens + msg.usage.output_tokens} tok
                    </span>
                  )}
                  {msg.usage.cache_read_tokens > 0 && (
                    <span className="text-[10px] text-gray-600 font-mono tabular-nums">
                      {msg.usage.cache_read_tokens} cached
                    </span>
                  )}
                  {msg.usage.tool_calls > 0 && (
                    <span className="text-[10px] text-gray-600 font-mono tabular-nums">
                      {msg.usage.tool_calls} tool{msg.usage.tool_calls !== 1 ? "s" : ""}
                    </span>
                  )}
                  {msg.usage.num_turns > 1 && (
                    <span className="text-[10px] text-gray-600 font-mono tabular-nums">
                      {msg.usage.num_turns} turns
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* ─── Input bar ─── */}
      <div className="pt-4 border-t border-white/[0.06]">
        <form onSubmit={handleSubmit} className="relative">
          <div className="flex items-end gap-2 bg-[#111] border border-white/[0.06] rounded-xl px-3 py-2 focus-within:border-blue-500/30 transition-colors">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={chatMode === "rag" ? "Ask a question (RAG)..." : "Ask a question (Direct)..."}
              className="flex-1 bg-transparent py-2 text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none"
              disabled={streaming}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
            />

            {streaming ? (
              <button
                type="button"
                onClick={handleStop}
                className="flex-shrink-0 w-8 h-8 rounded-lg bg-red-500/15 border border-red-500/20 flex items-center justify-center text-red-400 hover:bg-red-500/25 transition-colors mb-0.5"
              >
                <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                  <rect x="6" y="6" width="12" height="12" rx="1" />
                </svg>
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim()}
                className="flex-shrink-0 w-8 h-8 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 disabled:text-gray-600 flex items-center justify-center text-white transition-colors disabled:cursor-not-allowed mb-0.5"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5 12 3m0 0 7.5 7.5M12 3v18" />
                </svg>
              </button>
            )}
          </div>
        </form>
      </div>
      </div>{/* close main chat area */}
    </div>
  );
}
