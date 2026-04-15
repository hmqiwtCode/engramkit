"use client";

import { Wrench, X } from "lucide-react";
import { useState } from "react";

import type { ToolCall } from "../types";
import { summariseToolInput } from "../lib/toolSummary";

export function ToolCallPills({
  toolCalls,
  streaming,
}: {
  toolCalls: ToolCall[];
  streaming: boolean;
}) {
  const [openIdx, setOpenIdx] = useState<number | null>(null);
  if (toolCalls.length === 0) return null;

  return (
    <div className="mt-2 pt-2 border-t border-white/[0.04] space-y-1.5">
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-gray-600 uppercase tracking-wider">Tool Calls</span>
        <span className="text-[10px] text-gray-700 font-mono tabular-nums">{toolCalls.length}</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {toolCalls.map((tool, ti) => (
          <ToolPill
            key={ti}
            tool={tool}
            open={openIdx === ti}
            pending={tool.result === undefined && streaming}
            onToggle={() => setOpenIdx(openIdx === ti ? null : ti)}
          />
        ))}
      </div>
      {openIdx !== null && toolCalls[openIdx] && (
        <ToolDetail tool={toolCalls[openIdx]} onClose={() => setOpenIdx(null)} />
      )}
    </div>
  );
}

function paletteFor(tool: ToolCall) {
  if (tool.isError) return "border-red-500/25 bg-red-500/10 text-red-400";
  if (tool.isEngramkit) return "border-indigo-500/25 bg-indigo-500/10 text-indigo-300";
  return "border-amber-500/20 bg-amber-500/10 text-amber-400";
}

function ToolPill({
  tool,
  open,
  pending,
  onToggle,
}: {
  tool: ToolCall;
  open: boolean;
  pending: boolean;
  onToggle: () => void;
}) {
  const summary = summariseToolInput(tool);
  return (
    <button
      onClick={onToggle}
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-mono transition-colors hover:brightness-125 ${paletteFor(tool)} ${open ? "ring-1 ring-white/10" : ""}`}
      title={tool.fullName ?? tool.name}
    >
      <Wrench className="w-2.5 h-2.5 flex-shrink-0" strokeWidth={2} />
      <span className="font-medium">{tool.name}</span>
      {summary && <span className="opacity-70 truncate max-w-[180px]">· {summary}</span>}
      {pending && <span className="w-1 h-1 rounded-full bg-current animate-pulse ml-0.5" />}
    </button>
  );
}

function ToolDetail({ tool, onClose }: { tool: ToolCall; onClose: () => void }) {
  const hasInput = tool.input && Object.keys(tool.input).length > 0;
  const accent = tool.isEngramkit ? "text-indigo-300" : "text-amber-400";
  return (
    <div className="mt-2 bg-[#0a0a0a] border border-white/[0.04] rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/[0.04]">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`text-[10px] font-mono ${accent}`}>{tool.fullName ?? tool.name}</span>
          {tool.isError && (
            <span className="text-[9px] text-red-400 font-mono uppercase">error</span>
          )}
        </div>
        <button onClick={onClose} className="text-gray-600 hover:text-gray-400 transition-colors">
          <X className="w-3 h-3" strokeWidth={2} />
        </button>
      </div>
      {hasInput && (
        <div className="px-3 py-2 border-b border-white/[0.04]">
          <div className="text-[9px] text-gray-600 uppercase tracking-wider mb-1">Input</div>
          <pre className="text-[11px] text-gray-400 leading-relaxed font-mono whitespace-pre-wrap break-words">
            {JSON.stringify(tool.input, null, 2)}
          </pre>
        </div>
      )}
      <div className="px-3 py-2">
        <div className="text-[9px] text-gray-600 uppercase tracking-wider mb-1">
          Result{tool.result === undefined ? " (pending…)" : ""}
        </div>
        {tool.result !== undefined ? (
          <pre
            className={`text-[11px] leading-relaxed font-mono whitespace-pre-wrap break-words max-h-64 overflow-y-auto ${
              tool.isError ? "text-red-300" : "text-gray-400"
            }`}
          >
            {tool.result || "(empty)"}
          </pre>
        ) : (
          <PendingDots />
        )}
      </div>
    </div>
  );
}

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
