"use client";

import { ChevronDown, ChevronRight, Wrench } from "lucide-react";
import { Children, isValidElement, memo, useMemo, useState, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { summariseToolInput } from "../lib/toolSummary";
import type { BubbleSegment, Citation, ToolCall } from "../types";
import { CitationChip } from "./CitationChip";
import { buildPathMap, linkFilePathsInChildren } from "./FilePathLink";
import { Section, ToolInputBody, ToolResultBody } from "./toolResults";

interface SegmentViewProps {
  segment: BubbleSegment;
  isStreamingTail: boolean;
  citations: Citation[];
}

/** Render one timeline segment — either markdown text (with citation chips) or an inline tool call. */
export function SegmentView({ segment, isStreamingTail, citations }: SegmentViewProps) {
  if (segment.kind === "text") {
    return (
      <TextSegment
        content={segment.content}
        withCursor={isStreamingTail}
        citations={citations}
      />
    );
  }
  return <ToolSegment call={segment.call} live={isStreamingTail} />;
}

/* ────────────────── Text segments ────────────────── */

interface TextSegmentProps {
  content: string;
  withCursor: boolean;
  citations: Citation[];
}

function TextSegment({ content, withCursor, citations }: TextSegmentProps) {
  if (!withCursor) return <FrozenTextSegment content={content} citations={citations} />;
  return (
    <MarkdownBody citations={citations} content={content}>
      <span className="inline-block w-0.5 h-4 bg-blue-400 animate-pulse ml-0.5 align-text-bottom" />
    </MarkdownBody>
  );
}

/** A frozen text chunk memoised so earlier segments don't reparse Markdown
 *  when new content arrives at the end. Registry is included in the memo key
 *  so new tool-retrieved citations still link retroactively. */
const FrozenTextSegment = memo(
  function FrozenTextSegment({
    content,
    citations,
  }: {
    content: string;
    citations: Citation[];
  }) {
    return <MarkdownBody content={content} citations={citations} />;
  },
  (a, b) =>
    a.content === b.content &&
    a.citations === b.citations &&
    a.citations.length === b.citations.length,
);

interface MarkdownBodyProps {
  content: string;
  citations: Citation[];
  children?: ReactNode;
}

function MarkdownBody({ content, citations, children }: MarkdownBodyProps) {
  const components = useMarkdownComponents(citations);
  const patched = useMemo(() => ensureFootnoteDefs(content), [content]);
  return (
    <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-[#0a0a0a] prose-pre:border prose-pre:border-white/[0.06] prose-code:text-blue-300 prose-code:font-mono prose-headings:text-gray-100 prose-a:text-blue-400">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {patched}
      </ReactMarkdown>
      {children}
    </div>
  );
}

/**
 * GFM footnotes only activate when BOTH `[^N]` references AND `[^N]: definition`
 * lines exist. Our model emits references without definitions (we own the
 * References panel), so remark-gfm leaves the markers as literal text. Inject
 * placeholder definitions for any missing ones — the `<section data-footnotes>`
 * suppressor in `useMarkdownComponents` hides the resulting definitions block.
 */
function ensureFootnoteDefs(content: string): string {
  if (!content) return content;
  const referenced = new Set<string>();
  const defined = new Set<string>();

  const refRe = /\[\^([A-Za-z0-9_-]+)\]/g;
  let m: RegExpExecArray | null;
  while ((m = refRe.exec(content)) !== null) referenced.add(m[1]);

  const defRe = /^\[\^([A-Za-z0-9_-]+)\]:/gm;
  while ((m = defRe.exec(content)) !== null) defined.add(m[1]);

  const missing = [...referenced].filter((n) => !defined.has(n));
  if (missing.length === 0) return content;

  const stubs = missing.map((n) => `[^${n}]: .`).join("\n");
  // Two newlines so remark sees the defs as a separate block.
  return `${content}\n\n${stubs}`;
}

/**
 * Build the ReactMarkdown component overrides that:
 *   1. Replace `[^N]` footnote <sup> with our CitationChip.
 *   2. Auto-link raw file paths (only when they match a registry entry).
 *   3. Hide the footnote-definitions <section> that remark-gfm appends.
 */
function useMarkdownComponents(citations: Citation[]): Components {
  return useMemo(() => {
    const pathMap = buildPathMap(citations);
    const byIndex = new Map<number, Citation>();
    for (const c of citations) byIndex.set(c.index, c);

    const walk = (children: ReactNode) => linkFilePathsInChildren(children, pathMap);

    return {
      p: ({ children, ...rest }) => <p {...rest}>{walk(children)}</p>,
      li: ({ children, ...rest }) => <li {...rest}>{walk(children)}</li>,
      td: ({ children, ...rest }) => <td {...rest}>{walk(children)}</td>,
      th: ({ children, ...rest }) => <th {...rest}>{walk(children)}</th>,
      sup: (props) => {
        const ref = extractFootnoteRef(props.children);
        if (ref === null) return <sup {...props} />;
        const citation = byIndex.get(ref);
        return (
          <CitationChip
            citation={citation}
            rawMarker={String(ref)}
            anchorId={citation ? `cite-${citation.index}` : undefined}
          />
        );
      },
      // remark-gfm appends <section data-footnotes> with the definitions list —
      // hide it since we render our own registry-driven CitationsPanel below
      // the message. A `data-footnotes` attr or `#footnote-label` anchor is
      // the cleanest thing to sniff on.
      section: (props) => {
        if (isFootnoteSection(props as { className?: string } & Record<string, unknown>))
          return null;
        return <section {...props} />;
      },
    } satisfies Components;
  }, [citations]);
}

/** Detect `[^N]` footnote refs rendered as `<sup><a data-footnote-ref>N</a></sup>`. */
function extractFootnoteRef(children: ReactNode): number | null {
  const arr = Children.toArray(children);
  for (const child of arr) {
    if (!isValidElement(child)) continue;
    const el = child as React.ReactElement<{
      "data-footnote-ref"?: boolean | string;
      children?: ReactNode;
    }>;
    if (el.props["data-footnote-ref"] === undefined) continue;
    const text = extractTextContent(el.props.children);
    const n = parseInt(text.trim(), 10);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

function extractTextContent(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(extractTextContent).join("");
  if (isValidElement(node)) {
    const el = node as React.ReactElement<{ children?: ReactNode }>;
    return extractTextContent(el.props.children);
  }
  return "";
}

function isFootnoteSection(props: { className?: string } & Record<string, unknown>): boolean {
  if (props["data-footnotes"] !== undefined) return true;
  if (typeof props.className === "string" && props.className.includes("footnotes")) return true;
  return false;
}

/* ────────────────── Tool segments ────────────────── */

function ToolSegment({ call, live }: { call: ToolCall; live: boolean }) {
  const [open, setOpen] = useState(false);
  const summary = summariseToolInput(call);
  const pending = call.result === undefined && live;

  const palette = call.isError
    ? "border-red-500/25 bg-red-500/10 text-red-400"
    : call.isEngramkit
      ? "border-indigo-500/25 bg-indigo-500/10 text-indigo-300"
      : "border-amber-500/20 bg-amber-500/10 text-amber-400";

  return (
    <div className="not-prose my-2">
      <button
        onClick={() => setOpen((o) => !o)}
        className={`w-full flex items-center gap-2 px-2 py-1 rounded-md border text-left transition-colors hover:brightness-125 ${palette} ${open ? "rounded-b-none" : ""}`}
        title={call.fullName ?? call.name}
      >
        {open ? (
          <ChevronDown className="w-3 h-3 shrink-0 opacity-70" />
        ) : (
          <ChevronRight className="w-3 h-3 shrink-0 opacity-70" />
        )}
        <Wrench className="w-3 h-3 shrink-0 opacity-70" strokeWidth={2} />
        <span className="text-[11px] font-mono font-medium">{call.name}</span>
        {summary && (
          <span className="text-[11px] font-mono opacity-70 truncate flex-1">· {summary}</span>
        )}
        {pending && <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse shrink-0" />}
        {!pending && call.result !== undefined && !call.isError && (
          <span className="text-[10px] font-mono opacity-50 shrink-0">✓</span>
        )}
      </button>

      {open && (
        <div
          className={`border-x border-b rounded-b-md ${palette.replace(/bg-[^\s]+/, "bg-[#0a0a0a]")} p-2.5 space-y-2.5`}
        >
          {call.input && Object.keys(call.input).length > 0 && (
            <Section label="Input">
              <ToolInputBody input={call.input} />
            </Section>
          )}
          <Section label={`Result${call.result === undefined ? " · pending" : ""}`}>
            <ToolResultBody tool={call} />
          </Section>
        </div>
      )}
    </div>
  );
}
