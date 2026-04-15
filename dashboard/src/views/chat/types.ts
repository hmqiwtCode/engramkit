export interface Source {
  file: string;
  score: number;
  content?: string;
  wing?: string;
  room?: string;
  content_hash?: string;
}

export interface ToolCall {
  name: string;
  fullName?: string;
  input?: Record<string, unknown>;
  result?: string;
  isError?: boolean;
  isEngramkit?: boolean;
}

export interface Usage {
  total_cost_usd: number;
  duration_ms: number;
  tool_calls: number;
  num_turns: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  mode?: string;
}

export type BubbleSegment =
  | { kind: "text"; content: string }
  | { kind: "tool"; call: ToolCall };

export interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  /** Ordered timeline of text + tool events. Newer messages use this. */
  segments?: BubbleSegment[];
  /** Legacy — flat list of tool calls without timeline ordering. Still populated
   *  for sessions saved before segments shipped; new messages keep it in sync
   *  so totals / badges stay correct. */
  toolCalls?: ToolCall[];
  usage?: Usage;
}

export type ChatMode = "rag" | "direct";

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
}

export interface HistoryEntry {
  role: "user" | "assistant";
  content: string;
}

/** Unified reference registry: RAG-seed sources + engramkit_search/recall tool
 *  results deduped by content_hash. Shared by inline citation chips and the
 *  bottom references panel so the UI never shows a chip without a target. */
export interface Citation {
  /** 1-indexed — matches `[^N]` markers the model emits. */
  index: number;
  file: string;
  content?: string;
  score?: number;
  wing?: string;
  room?: string;
  repo?: string;
  content_hash?: string;
  /** "seed" = arrived via RAG pre-search; "tool" = extracted from a tool result. */
  source: "seed" | "tool";
}

export interface SendChatArgs {
  message: string;
  mode: ChatMode;
  vault_ids: string[];
  n_context: number;
  history: HistoryEntry[];
}
