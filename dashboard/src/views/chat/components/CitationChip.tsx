"use client";

import * as HoverCardPrimitive from "@radix-ui/react-hover-card";
import { ExternalLink, FileText } from "lucide-react";

import { Badge } from "@/components/shared/badge";
import type { Citation } from "../types";

interface CitationChipProps {
  citation?: Citation;
  /** When `citation` is undefined we still render a neutral chip — gaps are
   *  surfaced explicitly (best practice: don't hide broken citations). */
  rawMarker?: string;
  /** ID attribute to anchor-scroll to (e.g., `cite-3`). */
  anchorId?: string;
}

/**
 * Inline citation marker. Keyboard-accessible click target (scrolls to the
 * full reference card below the message); HoverCard gives sighted users an
 * instant preview. Missing citations render as a greyed chip so users see
 * where the model claimed grounding but we couldn't resolve it.
 */
export function CitationChip({ citation, rawMarker, anchorId }: CitationChipProps) {
  const label = citation ? String(citation.index) : rawMarker ?? "?";

  if (!citation) {
    return (
      <sup
        className="not-prose inline-flex items-center justify-center min-w-[16px] h-[16px] px-1 ml-0.5 rounded text-[10px] font-mono font-semibold bg-gray-500/10 text-gray-500 border border-gray-500/20 align-text-top"
        title="Source unavailable — model cited a chunk we couldn't resolve"
        aria-label={`Citation ${label} (unresolved)`}
      >
        {label}
      </sup>
    );
  }

  const fileName = citation.file.split("/").pop() ?? citation.file;

  return (
    <HoverCardPrimitive.Root openDelay={120} closeDelay={80}>
      <HoverCardPrimitive.Trigger asChild>
        <a
          href={anchorId ? `#${anchorId}` : undefined}
          onClick={(e) => {
            if (!anchorId) return;
            // Prefer smooth scroll; anchor nav default would jump instantly.
            const el = document.getElementById(anchorId);
            if (el) {
              e.preventDefault();
              el.scrollIntoView({ behavior: "smooth", block: "center" });
              el.setAttribute("data-cite-flash", "true");
              window.setTimeout(() => el.removeAttribute("data-cite-flash"), 1200);
            }
          }}
          className="not-prose inline-flex items-center justify-center min-w-[16px] h-[16px] px-1 ml-0.5 rounded text-[10px] font-mono font-semibold bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/25 hover:border-indigo-500/50 transition-colors align-text-top no-underline cursor-pointer"
          aria-label={`Citation ${label}: ${fileName}${
            typeof citation.score === "number" ? `, score ${citation.score.toFixed(2)}` : ""
          }`}
        >
          {label}
        </a>
      </HoverCardPrimitive.Trigger>

      <HoverCardPrimitive.Portal>
        <HoverCardPrimitive.Content
          side="top"
          align="center"
          sideOffset={6}
          className="z-50 w-80 rounded-lg border border-white/[0.08] bg-[#0c0c0c] shadow-2xl shadow-black/50 p-3 text-[11px] animate-in fade-in-0 zoom-in-95 duration-100"
        >
          <div className="flex items-center gap-2 mb-2 pb-2 border-b border-white/[0.04]">
            <FileText className="w-3 h-3 text-indigo-300 shrink-0" strokeWidth={1.8} />
            <span className="text-gray-600 font-mono tabular-nums shrink-0">
              [{citation.index}]
            </span>
            <span className="text-blue-400/80 font-mono truncate flex-1">{citation.file}</span>
          </div>

          <div className="flex flex-wrap items-center gap-1.5 mb-2">
            {citation.repo && (
              <span className="text-[10px] text-indigo-300/70 font-mono">{citation.repo}</span>
            )}
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
              <span className="text-[10px] text-gray-500 font-mono tabular-nums ml-auto">
                score {citation.score.toFixed(3)}
              </span>
            )}
            <span
              className={`text-[9px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded ${
                citation.source === "tool"
                  ? "bg-amber-500/10 text-amber-400/80 border border-amber-500/20"
                  : "bg-blue-500/10 text-blue-400/80 border border-blue-500/20"
              }`}
            >
              {citation.source === "tool" ? "via tool" : "seed"}
            </span>
          </div>

          {citation.content ? (
            <pre className="text-[11px] text-gray-400 leading-relaxed font-mono whitespace-pre-wrap break-words max-h-40 overflow-y-auto">
              {citation.content.length > 800
                ? citation.content.slice(0, 800) + "\n…"
                : citation.content}
            </pre>
          ) : (
            <div className="text-[11px] text-gray-600 italic">No content preview.</div>
          )}

          <div className="mt-2 pt-2 border-t border-white/[0.04] flex items-center gap-1 text-[10px] text-gray-600">
            <ExternalLink className="w-2.5 h-2.5" strokeWidth={2} />
            <span>Click to jump to full reference below</span>
          </div>
        </HoverCardPrimitive.Content>
      </HoverCardPrimitive.Portal>
    </HoverCardPrimitive.Root>
  );
}
