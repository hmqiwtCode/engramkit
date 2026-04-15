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
 * Typewriter smoothing: text from `pushText` is buffered in `pending` and
 * drained into `segments` from a `requestAnimationFrame` loop. Network
 * bursts (multiple deltas arriving in one packet) no longer appear as
 * sudden jumps — the RAF loop bounds re-renders to ~60/sec and paces chars
 * so the visible text grows continuously. Rate is adaptive: floor at
 * `MIN_CHARS_PER_SEC`, otherwise drain the backlog within `LAG_BUDGET_MS`.
 *
 * On stream end, `finalise()` waits for the typewriter to fully drain
 * (so the committed message matches what the user just watched type)
 * before handing back the assembled `Message`.
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

const MIN_CHARS_PER_SEC = 260;
const LAG_BUDGET_MS = 250;

class StreamStore {
  private state: StreamState = EMPTY;
  private listeners = new Set<() => void>();
  /** tool_use index → position in `segments`, so tool_result can patch in-place. */
  private toolIndexToSegment = new Map<number, number>();

  /** Typewriter buffer — text that has arrived but hasn't been rendered yet. */
  private pending = "";
  private rafHandle: number | null = null;
  private lastTickTime = 0;
  /** Set when `finalise` is waiting for the typewriter to drain. */
  private drainCallback: (() => void) | null = null;

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
    this.cancelRaf();
    this.pending = "";
    this.drainCallback = null;
    this.state = { ...EMPTY, active: true };
    this.toolIndexToSegment = new Map();
    this.emit();
  }

  pushText(text: string) {
    if (!text) return;
    this.state.fullText += text;
    this.pending += text;
    this.ensureTicking();
  }

  pushToolCall(call: ToolCall, index: number) {
    // Flush pending text first so the tool call lands after the text that
    // preceded it on the wire — preserves chronological order in the timeline.
    this.flushPending();
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
    // Abort should feel immediate: dump whatever the typewriter hadn't
    // shown yet so the frozen bubble matches the fullText accumulator.
    this.flushPending();
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

  /**
   * Return the committed Message once the typewriter has fully drained.
   *
   * We deliberately wait for the RAF buffer to empty so the user sees the
   * last few characters type in rather than watching the frozen bubble
   * "snap" ahead of the animation.
   */
  finalise(): Promise<Message | null> {
    return new Promise((resolve) => {
      const commit = () => resolve(this.doFinalise());
      if (this.pending.length === 0) {
        commit();
        return;
      }
      this.drainCallback = commit;
    });
  }

  private doFinalise(): Message | null {
    this.cancelRaf();
    this.pending = "";
    this.drainCallback = null;

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

  // ── Typewriter internals ──────────────────────────────────────────────

  private ensureTicking() {
    if (this.rafHandle !== null) return;
    if (typeof requestAnimationFrame === "undefined") {
      // SSR / test environment — skip the animation, render immediately.
      this.flushPending();
      return;
    }
    this.lastTickTime = 0;
    this.rafHandle = requestAnimationFrame(this.tick);
  }

  private cancelRaf() {
    if (this.rafHandle !== null && typeof cancelAnimationFrame !== "undefined") {
      cancelAnimationFrame(this.rafHandle);
    }
    this.rafHandle = null;
    this.lastTickTime = 0;
  }

  private tick = (now: number) => {
    this.rafHandle = null;
    if (!this.lastTickTime) this.lastTickTime = now;
    const elapsed = now - this.lastTickTime;
    this.lastTickTime = now;

    if (this.pending.length > 0) {
      // Adaptive rate: drain within LAG_BUDGET_MS, never slower than the floor.
      const budget = Math.max(1, LAG_BUDGET_MS / 1000);
      const rate = Math.max(MIN_CHARS_PER_SEC, this.pending.length / budget);
      const take = Math.min(
        this.pending.length,
        Math.max(1, Math.floor((elapsed / 1000) * rate)),
      );
      const chunk = this.pending.slice(0, take);
      this.pending = this.pending.slice(take);
      this.appendTextToSegments(chunk);
      this.emit();
    }

    if (this.pending.length > 0) {
      this.rafHandle = requestAnimationFrame(this.tick);
      return;
    }

    this.lastTickTime = 0;
    // Buffer is empty — if finalise was waiting, run it now.
    if (this.drainCallback) {
      const cb = this.drainCallback;
      this.drainCallback = null;
      cb();
    }
  };

  private flushPending() {
    this.cancelRaf();
    if (this.pending.length === 0) return;
    this.appendTextToSegments(this.pending);
    this.pending = "";
    this.emit();
  }

  private appendTextToSegments(text: string) {
    const segments = this.state.segments;
    const last = segments[segments.length - 1];
    if (last && last.kind === "text") {
      segments[segments.length - 1] = { kind: "text", content: last.content + text };
    } else {
      segments.push({ kind: "text", content: text });
    }
  }
}

export const streamStore = new StreamStore();
