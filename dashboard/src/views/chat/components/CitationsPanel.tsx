"use client";

import { ChevronDown, ChevronRight, FileText } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/shared/badge";
import type { Citation } from "../types";

/**
 * Full references panel below an assistant message. Lists every citation in
 * the registry — RAG-seed sources PLUS tool-retrieved chunks — with anchor
 * IDs (`cite-N`) that inline CitationChips link to.
 *
 * Collapsed by default to reduce visual noise on long answers; the chip-click
 * scroll targets the expanded card (auto-expands on demand).
 */
export function CitationsPanel({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;
  return (
    <div className="mt-3 pt-3 border-t border-white/[0.06]">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[10px] text-gray-600 uppercase tracking-wider">
          References ({citations.length})
        </span>
      </div>
      <div className="space-y-1">
        {citations.map((c) => (
          <CitationCard key={c.index} citation={c} />
        ))}
      </div>
    </div>
  );
}

function CitationCard({ citation }: { citation: Citation }) {
  const [open, setOpen] = useState(false);
  const anchorId = `cite-${citation.index}`;

  return (
    <div
      id={anchorId}
      className="border border-white/[0.04] rounded-md bg-[#0c0c0c] overflow-hidden scroll-mt-24 data-[cite-flash=true]:border-indigo-400/60 data-[cite-flash=true]:shadow-[0_0_0_2px_rgba(129,140,248,0.2)] transition-colors duration-500"
    >
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-2 py-1.5 hover:bg-white/[0.02] transition-colors text-left"
      >
        {open ? (
          <ChevronDown className="w-3 h-3 text-gray-600 shrink-0" />
        ) : (
          <ChevronRight className="w-3 h-3 text-gray-600 shrink-0" />
        )}
        <span className="text-[10px] text-indigo-300 font-mono font-semibold tabular-nums shrink-0 min-w-[18px]">
          [{citation.index}]
        </span>
        <FileText className="w-3 h-3 text-gray-500 shrink-0" strokeWidth={1.8} />
        {citation.repo && (
          <span className="text-[10px] text-indigo-300/70 font-mono shrink-0">{citation.repo}</span>
        )}
        <span className="text-[11px] text-blue-400/80 font-mono truncate flex-1">
          {citation.file}
        </span>
        {citation.wing && (
          <Badge
            variant={
              citation.wing === "semantic"
                ? "semantic"
                : citation.wing === "lexical"
                  ? "lexical"
                  : "default"
            }
          >
            {citation.wing}
          </Badge>
        )}
        {citation.room && <Badge>{citation.room}</Badge>}
        {typeof citation.score === "number" && (
          <span className="text-[10px] text-gray-600 font-mono tabular-nums shrink-0">
            {citation.score.toFixed(3)}
          </span>
        )}
        <span
          className={`text-[9px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded shrink-0 ${
            citation.source === "tool"
              ? "bg-amber-500/10 text-amber-400/80 border border-amber-500/20"
              : "bg-blue-500/10 text-blue-400/80 border border-blue-500/20"
          }`}
        >
          {citation.source === "tool" ? "tool" : "seed"}
        </span>
      </button>
      {open && citation.content && (
        <div className="px-2 pb-2 border-t border-white/[0.04]">
          <pre className="text-[11px] text-gray-400 leading-relaxed font-mono whitespace-pre-wrap break-words max-h-48 overflow-y-auto mt-2">
            {citation.content}
          </pre>
        </div>
      )}
      {open && !citation.content && (
        <div className="px-2 pb-2 border-t border-white/[0.04] pt-2">
          <span className="text-[11px] text-gray-600 italic">No content preview available.</span>
        </div>
      )}
    </div>
  );
}
