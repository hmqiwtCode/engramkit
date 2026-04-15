"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import { useState, type ReactNode } from "react";

import { Badge } from "@/components/shared/badge";
import { tryParseJson } from "../lib/parseToolResult";
import type { ToolCall } from "../types";

/** Render the result body for a tool call. Dispatches on `tool.name`. */
export function ToolResultBody({ tool }: { tool: ToolCall }) {
  if (tool.result === undefined) return <PendingDots />;
  if (tool.isError) return <ErrorText text={tool.result} />;

  const renderer = RENDERERS[tool.name];
  if (renderer) return renderer(tool);
  return <GenericResult tool={tool} />;
}

/* ────────────────── Dispatch table ────────────────── */

type Renderer = (tool: ToolCall) => ReactNode;

const RENDERERS: Record<string, Renderer> = {
  engramkit_search: (tool) => <EngramkitSearchResult tool={tool} />,
  engramkit_recall: (tool) => <EngramkitRecallResult tool={tool} />,
  engramkit_wake_up: (tool) => <EngramkitWakeUpResult tool={tool} />,
  engramkit_status: (tool) => <EngramkitStatusResult tool={tool} />,
  engramkit_kg_query: (tool) => <EngramkitKgQueryResult tool={tool} />,
  engramkit_kg_timeline: (tool) => <EngramkitKgTimelineResult tool={tool} />,
  engramkit_save: (tool) => <EngramkitSaveResult tool={tool} />,
  engramkit_kg_add: (tool) => <EngramkitSaveResult tool={tool} />,
  engramkit_diary_write: (tool) => <EngramkitSaveResult tool={tool} />,
  Read: (tool) => <FileReadResult tool={tool} />,
  Grep: (tool) => <GrepResult tool={tool} />,
  Glob: (tool) => <GlobResult tool={tool} />,
};

/* ────────────────── Building blocks ────────────────── */

function PendingDots() {
  return (
    <div className="flex items-center gap-1.5 text-[11px] text-gray-600 italic">
      <span className="w-1 h-1 rounded-full bg-gray-500 animate-pulse" />
      <span className="w-1 h-1 rounded-full bg-gray-500 animate-pulse [animation-delay:150ms]" />
      <span className="w-1 h-1 rounded-full bg-gray-500 animate-pulse [animation-delay:300ms]" />
      <span className="ml-1">waiting for tool response</span>
    </div>
  );
}

function ErrorText({ text }: { text: string }) {
  return (
    <pre className="text-[11px] text-red-300 leading-relaxed font-mono whitespace-pre-wrap break-words max-h-48 overflow-y-auto">
      {text || "(empty error)"}
    </pre>
  );
}

function Section({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-1">
      <div className="text-[9px] text-gray-600 uppercase tracking-wider">{label}</div>
      {children}
    </div>
  );
}

function CodePre({ children, max = "max-h-64" }: { children: string; max?: string }) {
  return (
    <pre
      className={`text-[11px] text-gray-400 leading-relaxed font-mono whitespace-pre-wrap break-words overflow-y-auto ${max}`}
    >
      {children}
    </pre>
  );
}

function KVRow({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="flex items-start gap-2 text-[11px]">
      <span className="text-gray-600 font-mono shrink-0 min-w-[80px]">{k}</span>
      <span className="text-gray-300 font-mono break-all">{v}</span>
    </div>
  );
}

/* ────────────────── Generic fallback (collapsible JSON tree) ────────────────── */

function GenericResult({ tool }: { tool: ToolCall }) {
  const parsed = tryParseJson(tool.result);
  if (parsed === null) return <CodePre>{tool.result || "(empty)"}</CodePre>;
  return <JsonTree value={parsed} defaultOpen />;
}

function JsonTree({ value, defaultOpen = false }: { value: unknown; defaultOpen?: boolean }) {
  if (value === null) return <span className="text-gray-500 font-mono text-[11px]">null</span>;
  if (typeof value === "boolean")
    return <span className="text-amber-300 font-mono text-[11px]">{String(value)}</span>;
  if (typeof value === "number")
    return <span className="text-cyan-300 font-mono text-[11px]">{value}</span>;
  if (typeof value === "string")
    return (
      <span className="text-emerald-300 font-mono text-[11px] break-all">
        &quot;{value.length > 120 ? value.slice(0, 120) + "…" : value}&quot;
      </span>
    );
  if (Array.isArray(value)) return <JsonArray items={value} defaultOpen={defaultOpen} />;
  if (typeof value === "object")
    return <JsonObject obj={value as Record<string, unknown>} defaultOpen={defaultOpen} />;
  return <span className="text-gray-400 font-mono text-[11px]">{String(value)}</span>;
}

function JsonObject({
  obj,
  defaultOpen,
}: {
  obj: Record<string, unknown>;
  defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const entries = Object.entries(obj);
  if (entries.length === 0) return <span className="text-gray-500 font-mono text-[11px]">{"{}"}</span>;

  return (
    <div className="text-[11px]">
      <button
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-1 text-gray-500 hover:text-gray-300 transition-colors"
      >
        {open ? <ChevronDown className="w-2.5 h-2.5" /> : <ChevronRight className="w-2.5 h-2.5" />}
        <span className="font-mono">
          {"{"}
          {!open && ` ${entries.length} keys `}
          {!open && "}"}
        </span>
      </button>
      {open && (
        <div className="ml-3 border-l border-white/[0.06] pl-2 space-y-0.5 mt-0.5">
          {entries.map(([k, v]) => (
            <div key={k} className="flex items-start gap-2">
              <span className="text-indigo-300/80 font-mono shrink-0">{k}:</span>
              <JsonTree value={v} />
            </div>
          ))}
          <div className="font-mono text-gray-500">{"}"}</div>
        </div>
      )}
    </div>
  );
}

function JsonArray({ items, defaultOpen }: { items: unknown[]; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  if (items.length === 0) return <span className="text-gray-500 font-mono text-[11px]">[]</span>;

  return (
    <div className="text-[11px]">
      <button
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-1 text-gray-500 hover:text-gray-300 transition-colors"
      >
        {open ? <ChevronDown className="w-2.5 h-2.5" /> : <ChevronRight className="w-2.5 h-2.5" />}
        <span className="font-mono">
          [
          {!open && ` ${items.length} items `}
          {!open && "]"}
        </span>
      </button>
      {open && (
        <div className="ml-3 border-l border-white/[0.06] pl-2 space-y-0.5 mt-0.5">
          {items.slice(0, 50).map((v, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="text-gray-600 font-mono shrink-0 min-w-[20px]">{i}:</span>
              <JsonTree value={v} />
            </div>
          ))}
          {items.length > 50 && (
            <div className="text-gray-600 font-mono italic">… {items.length - 50} more</div>
          )}
          <div className="font-mono text-gray-500">]</div>
        </div>
      )}
    </div>
  );
}

/* ────────────────── Engramkit tool renderers ────────────────── */

interface SearchHit {
  file_path?: string;
  score?: number;
  content?: string;
  wing?: string;
  room?: string;
  _repo?: string;
}

function EngramkitSearchResult({ tool }: { tool: ToolCall }) {
  const parsed = tryParseJson(tool.result) as
    | { query?: string; results?: SearchHit[]; count?: number }
    | null;
  if (!parsed) return <GenericResult tool={tool} />;
  const results = parsed.results ?? [];

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-[10px] text-gray-500 font-mono">
        <span className="text-gray-400">query</span>
        <span className="text-emerald-300">&quot;{parsed.query}&quot;</span>
        <span className="text-gray-600">· {results.length} hits</span>
      </div>
      {results.length === 0 ? (
        <div className="text-[11px] text-gray-500 italic">No results.</div>
      ) : (
        <div className="space-y-1.5">
          {results.map((hit, i) => (
            <ChunkCard key={i} hit={hit} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}

function ChunkCard({ hit, index }: { hit: SearchHit; index: number }) {
  const [open, setOpen] = useState(false);
  const file = hit.file_path ?? "?";
  return (
    <div className="border border-white/[0.04] rounded bg-[#0c0c0c] overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-2 py-1.5 hover:bg-white/[0.02] transition-colors text-left"
      >
        <span className="text-[10px] text-gray-600 font-mono shrink-0">[{index + 1}]</span>
        {hit._repo && (
          <span className="text-[10px] text-indigo-300/70 font-mono shrink-0">{hit._repo}</span>
        )}
        <span className="text-[11px] text-blue-400/80 font-mono truncate flex-1">{file}</span>
        {hit.wing && (
          <Badge
            variant={
              hit.wing === "semantic" ? "semantic" : hit.wing === "lexical" ? "lexical" : "default"
            }
          >
            {hit.wing}
          </Badge>
        )}
        {typeof hit.score === "number" && (
          <span className="text-[10px] text-gray-600 font-mono tabular-nums shrink-0">
            {hit.score.toFixed(3)}
          </span>
        )}
        {open ? (
          <ChevronDown className="w-3 h-3 text-gray-600 shrink-0" />
        ) : (
          <ChevronRight className="w-3 h-3 text-gray-600 shrink-0" />
        )}
      </button>
      {open && hit.content && (
        <div className="px-2 pb-2 border-t border-white/[0.04]">
          <CodePre max="max-h-40">{hit.content}</CodePre>
        </div>
      )}
    </div>
  );
}

function EngramkitRecallResult({ tool }: { tool: ToolCall }) {
  const parsed = tryParseJson(tool.result) as
    | { wing?: string; room?: string; recalls?: Array<{ repo?: string; text?: string; tokens?: number }> }
    | null;
  if (!parsed) return <GenericResult tool={tool} />;
  const recalls = parsed.recalls ?? [];

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-[10px] text-gray-500 font-mono">
        {parsed.wing && <span>wing:{parsed.wing}</span>}
        {parsed.room && <span>room:{parsed.room}</span>}
        <span className="text-gray-600">· {recalls.length} repo(s)</span>
      </div>
      {recalls.map((r, i) => (
        <div key={i} className="border border-white/[0.04] rounded bg-[#0c0c0c] p-2">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] text-indigo-300/70 font-mono">{r.repo}</span>
            {typeof r.tokens === "number" && (
              <span className="text-[10px] text-gray-600 font-mono tabular-nums">
                {r.tokens} tok
              </span>
            )}
          </div>
          <CodePre max="max-h-32">{r.text ?? ""}</CodePre>
        </div>
      ))}
    </div>
  );
}

function EngramkitWakeUpResult({ tool }: { tool: ToolCall }) {
  const parsed = tryParseJson(tool.result) as
    | { context?: string; total_tokens?: number }
    | null;
  if (!parsed) return <GenericResult tool={tool} />;
  return (
    <div className="space-y-1.5">
      {typeof parsed.total_tokens === "number" && (
        <div className="text-[10px] text-gray-600 font-mono">{parsed.total_tokens} tok loaded</div>
      )}
      {parsed.context && <CodePre max="max-h-48">{parsed.context}</CodePre>}
    </div>
  );
}

function EngramkitStatusResult({ tool }: { tool: ToolCall }) {
  const parsed = tryParseJson(tool.result) as
    | {
        vaults?: Array<{
          repo?: string;
          total_chunks?: number;
          total_files?: number;
          stale_chunks?: number;
          generation?: number;
        }>;
      }
    | null;
  if (!parsed?.vaults) return <GenericResult tool={tool} />;
  return (
    <div className="space-y-1.5">
      {parsed.vaults.map((v, i) => (
        <div key={i} className="border border-white/[0.04] rounded bg-[#0c0c0c] p-2 space-y-1">
          <div className="text-[11px] text-indigo-300/80 font-mono">{v.repo}</div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
            <KVRow k="chunks" v={v.total_chunks ?? 0} />
            <KVRow k="files" v={v.total_files ?? 0} />
            <KVRow k="stale" v={v.stale_chunks ?? 0} />
            <KVRow k="generation" v={v.generation ?? 0} />
          </div>
        </div>
      ))}
    </div>
  );
}

function EngramkitKgQueryResult({ tool }: { tool: ToolCall }) {
  const parsed = tryParseJson(tool.result) as
    | {
        entity?: string;
        facts?: Array<{
          subject?: string;
          predicate?: string;
          object?: string;
          valid_from?: string;
          valid_to?: string;
        }>;
        count?: number;
      }
    | null;
  if (!parsed?.facts) return <GenericResult tool={tool} />;
  return (
    <div className="space-y-1.5">
      <div className="text-[10px] text-gray-500 font-mono">
        <span className="text-gray-400">entity</span>{" "}
        <span className="text-indigo-300">{parsed.entity}</span>
        <span className="text-gray-600"> · {parsed.facts.length} facts</span>
      </div>
      {parsed.facts.length === 0 ? (
        <div className="text-[11px] text-gray-500 italic">No facts found.</div>
      ) : (
        <div className="space-y-0.5">
          {parsed.facts.map((f, i) => (
            <FactRow key={i} fact={f} />
          ))}
        </div>
      )}
    </div>
  );
}

function EngramkitKgTimelineResult({ tool }: { tool: ToolCall }) {
  const parsed = tryParseJson(tool.result) as
    | {
        timeline?: Array<{
          subject?: string;
          predicate?: string;
          object?: string;
          valid_from?: string;
          valid_to?: string;
        }>;
        count?: number;
      }
    | null;
  if (!parsed?.timeline) return <GenericResult tool={tool} />;
  return (
    <div className="space-y-0.5">
      <div className="text-[10px] text-gray-500 font-mono">
        {parsed.timeline.length} events
      </div>
      {parsed.timeline.map((f, i) => (
        <FactRow key={i} fact={f} showDate />
      ))}
    </div>
  );
}

function FactRow({
  fact,
  showDate = false,
}: {
  fact: {
    subject?: string;
    predicate?: string;
    object?: string;
    valid_from?: string;
    valid_to?: string;
  };
  showDate?: boolean;
}) {
  return (
    <div className="flex items-center gap-2 text-[11px] font-mono border border-white/[0.04] rounded bg-[#0c0c0c] px-2 py-1">
      <span className="text-indigo-300 truncate">{fact.subject}</span>
      <span className="text-gray-500 shrink-0">·</span>
      <span className="text-amber-300 truncate">{fact.predicate}</span>
      <span className="text-gray-500 shrink-0">·</span>
      <span className="text-emerald-300 truncate flex-1">{fact.object}</span>
      {showDate && fact.valid_from && (
        <span className="text-[10px] text-gray-600 shrink-0">{fact.valid_from}</span>
      )}
      {fact.valid_to && (
        <span className="text-[10px] text-red-400/60 shrink-0">ended {fact.valid_to}</span>
      )}
    </div>
  );
}

function EngramkitSaveResult({ tool }: { tool: ToolCall }) {
  const parsed = tryParseJson(tool.result) as
    | { saved?: boolean; added?: boolean; content_hash?: string; triple_id?: string; tokens?: number }
    | null;
  if (!parsed) return <GenericResult tool={tool} />;
  return (
    <div className="flex items-center gap-2 text-[11px] font-mono">
      <Badge variant={parsed.saved || parsed.added ? "semantic" : "default"}>
        {parsed.saved ? "saved" : parsed.added ? "added" : "?"}
      </Badge>
      {parsed.content_hash && (
        <span className="text-gray-500">hash: {parsed.content_hash.slice(0, 12)}…</span>
      )}
      {parsed.triple_id && (
        <span className="text-gray-500 truncate">{parsed.triple_id}</span>
      )}
      {typeof parsed.tokens === "number" && (
        <span className="text-gray-600 ml-auto">{parsed.tokens} tok</span>
      )}
    </div>
  );
}

/* ────────────────── File tool renderers ────────────────── */

function FileReadResult({ tool }: { tool: ToolCall }) {
  const file = (tool.input?.file_path as string | undefined) ?? "";
  return (
    <div className="space-y-1">
      {file && (
        <div className="text-[10px] text-blue-400/80 font-mono truncate">{file}</div>
      )}
      <CodePre max="max-h-64">{tool.result ?? ""}</CodePre>
    </div>
  );
}

function GrepResult({ tool }: { tool: ToolCall }) {
  const pattern = (tool.input?.pattern as string | undefined) ?? "";
  const text = tool.result ?? "";
  const lines = text.split("\n").filter(Boolean);
  return (
    <div className="space-y-1">
      {pattern && (
        <div className="text-[10px] text-amber-300/80 font-mono">
          /{pattern.length > 60 ? pattern.slice(0, 60) + "…" : pattern}/
        </div>
      )}
      <div className="text-[10px] text-gray-600 font-mono">{lines.length} lines</div>
      <CodePre max="max-h-64">{text}</CodePre>
    </div>
  );
}

function GlobResult({ tool }: { tool: ToolCall }) {
  const glob = (tool.input?.pattern as string | undefined) ?? "";
  const text = tool.result ?? "";
  const paths = text.split("\n").filter(Boolean);
  return (
    <div className="space-y-1">
      {glob && (
        <div className="text-[10px] text-amber-300/80 font-mono">{glob}</div>
      )}
      <div className="text-[10px] text-gray-600 font-mono">{paths.length} files</div>
      <CodePre max="max-h-48">{text}</CodePre>
    </div>
  );
}

/* ────────────────── Shared tool input renderer ────────────────── */

export function ToolInputBody({ input }: { input: Record<string, unknown> | undefined }) {
  if (!input || Object.keys(input).length === 0) return null;
  return <JsonTree value={input} defaultOpen />;
}

export { Section };
