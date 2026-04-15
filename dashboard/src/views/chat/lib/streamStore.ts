import type { BubbleSegment, Message, Source, ToolCall, Usage } from "../types";

/**
 * External store for the in-flight assistant message.
 *
 * Why this exists: while streaming, we get dozens of SSE events per second.
 * If we wrote every event into the React `messages` array, the entire
 * MessageList would reconcile on every chunk. Instead we keep the streaming
 * bubble's state here and expose it via `useSyncExternalStore` — only the
 * single streaming bubble subscribes, and committed messages stay frozen.
 *
 * On stream end, `finalise()` hands back a plain `Message` to be appended
 * to the committed list in one `setMessages` call.
 */
export interface StreamState {
  active: boolean;
  segments: BubbleSegment[];
  sources?: Source[];
  usage?: Usage;
  mode?: string;
  /** Plain text accumulator — handy for the abort/error paths. */
  fullText: string;
}

const EMPTY: StreamState = { active: false, segments: [], fullText: "" };

class StreamStore {
  private state: StreamState = EMPTY;
  private listeners = new Set<() => void>();
  /** tool_use index → position in `segments`, so tool_result can patch in-place. */
  private toolIndexToSegment = new Map<number, number>();

  subscribe = (fn: () => void): (() => void) => {
    this.listeners.add(fn);
    return () => {
      this.listeners.delete(fn);
    };
  };

  getSnapshot = (): StreamState => this.state;
  getServerSnapshot = (): StreamState => EMPTY;

  private emit() {
    this.state = { ...this.state, segments: [...this.state.segments] };
    for (const fn of this.listeners) fn();
  }

  start() {
    this.state = { ...EMPTY, active: true };
    this.toolIndexToSegment = new Map();
    this.emit();
  }

  pushText(text: string) {
    if (!text) return;
    const segments = this.state.segments;
    const last = segments[segments.length - 1];
    if (last && last.kind === "text") {
      segments[segments.length - 1] = { kind: "text", content: last.content + text };
    } else {
      segments.push({ kind: "text", content: text });
    }
    this.state.fullText += text;
    this.emit();
  }

  pushToolCall(call: ToolCall, index: number) {
    this.state.segments.push({ kind: "tool", call });
    this.toolIndexToSegment.set(index, this.state.segments.length - 1);
    this.emit();
  }

  updateToolResult(index: number, result: string, isError: boolean) {
    const segIdx = this.toolIndexToSegment.get(index);
    if (segIdx === undefined) return;
    const seg = this.state.segments[segIdx];
    if (!seg || seg.kind !== "tool") return;
    this.state.segments[segIdx] = {
      kind: "tool",
      call: { ...seg.call, result, isError },
    };
    this.emit();
  }

  setSources(sources: Source[]) {
    this.state.sources = sources;
    this.emit();
  }

  setUsage(usage: Usage) {
    this.state.usage = usage;
    this.state.mode = usage.mode ?? this.state.mode;
    this.emit();
  }

  setMode(mode: string) {
    this.state.mode = mode;
    this.emit();
  }

  /** Mark any pending tool calls as aborted — user hit Stop. */
  markAbort() {
    for (let i = 0; i < this.state.segments.length; i++) {
      const seg = this.state.segments[i];
      if (seg.kind === "tool" && seg.call.result === undefined) {
        this.state.segments[i] = {
          kind: "tool",
          call: { ...seg.call, result: "(aborted)", isError: true },
        };
      }
    }
    this.emit();
  }

  finalise(): Message | null {
    if (!this.state.active && this.state.segments.length === 0) return null;

    const toolCalls: ToolCall[] = [];
    let content = "";
    for (const seg of this.state.segments) {
      if (seg.kind === "text") content += seg.content;
      else toolCalls.push(seg.call);
    }
    const msg: Message = {
      role: "assistant",
      content,
      segments: this.state.segments.slice(),
      toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
      sources: this.state.sources,
      usage: this.state.usage,
    };
    this.state = EMPTY;
    this.toolIndexToSegment = new Map();
    this.emit();
    return msg;
  }
}

export const streamStore = new StreamStore();
