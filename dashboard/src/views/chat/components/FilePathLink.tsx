"use client";

import { Children, cloneElement, isValidElement, type ReactNode } from "react";

import type { Citation } from "../types";
import { CitationChip } from "./CitationChip";

/** Matches `path/to/file.ext`, optional `:line` or `:line-line`. Deliberately
 *  conservative — requires an extension from an allow-list to avoid linking
 *  random dotted words. */
const FILE_PATH_RE =
  /([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:ts|tsx|jsx?|py|md|mdx|json|ya?ml|sh|rs|go|java|rb|toml|txt|sql|css|scss|html|c|cpp|h|hpp|swift|kt|php))(?::(\d+)(?:-(\d+))?)?/g;

/**
 * Wraps raw file-path tokens in the markdown output with CitationChips when
 * they match a known registry entry. Keeps walks surgical — we only descend
 * into strings and elements whose children could legitimately contain prose.
 */
export function linkFilePathsInChildren(
  children: ReactNode,
  citationsByPath: Map<string, Citation>,
): ReactNode {
  if (citationsByPath.size === 0) return children;

  const mapped = Children.map(children, (child) => transform(child, citationsByPath));
  return mapped;
}

function transform(node: ReactNode, map: Map<string, Citation>): ReactNode {
  if (typeof node === "string") return scanString(node, map);
  if (typeof node === "number" || typeof node === "boolean" || node == null) return node;
  if (Array.isArray(node)) return node.map((n) => transform(n, map));

  if (isValidElement(node)) {
    const el = node as React.ReactElement<{ children?: ReactNode }>;
    // Don't descend into code blocks / pre / a (already meaningful) or tool segments.
    const type = typeof el.type === "string" ? el.type : "";
    if (type === "code" || type === "pre" || type === "a") return el;
    const newChildren = Children.map(el.props.children, (c) => transform(c, map));
    return cloneElement(el, undefined, newChildren);
  }
  return node;
}

/** Split a text node into alternating plain/chip pieces. */
function scanString(text: string, map: Map<string, Citation>): ReactNode {
  FILE_PATH_RE.lastIndex = 0;
  let match: RegExpExecArray | null;
  const parts: ReactNode[] = [];
  let cursor = 0;
  let matchIdx = 0;

  while ((match = FILE_PATH_RE.exec(text)) !== null) {
    const [whole, path] = match;
    const citation = lookup(path, map);
    if (!citation) continue; // only link paths we can resolve

    if (match.index > cursor) parts.push(text.slice(cursor, match.index));
    parts.push(whole);
    parts.push(
      <CitationChip
        key={`fp-${matchIdx++}`}
        citation={citation}
        anchorId={`cite-${citation.index}`}
      />,
    );
    cursor = match.index + whole.length;
  }

  if (parts.length === 0) return text;
  if (cursor < text.length) parts.push(text.slice(cursor));
  return parts;
}

/** Match file paths against registry. Prefers exact match, then suffix match. */
function lookup(path: string, map: Map<string, Citation>): Citation | undefined {
  const exact = map.get(path);
  if (exact) return exact;
  for (const [k, v] of map) {
    if (k.endsWith(`/${path}`) || k === path) return v;
  }
  return undefined;
}

/** Build the path→citation lookup once per message. */
export function buildPathMap(citations: Citation[]): Map<string, Citation> {
  const m = new Map<string, Citation>();
  for (const c of citations) {
    if (c.file && c.file !== "?") m.set(c.file, c);
  }
  return m;
}
