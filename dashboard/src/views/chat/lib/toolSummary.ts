import type { ToolCall } from "../types";

/** Short preview of a tool call's input, shown inline in the pill. */
export function summariseToolInput(tool: ToolCall): string {
  const input = tool.input;
  if (!input || typeof input !== "object") return "";

  const pick = (key: string): string | null => {
    const value = (input as Record<string, unknown>)[key];
    return typeof value === "string" && value.length > 0 ? value : null;
  };

  const clip = (s: string, n = 48) => (s.length > n ? s.slice(0, n) + "…" : s);

  // Engramkit tools — most distinguishing field first.
  const query = pick("query");
  if (query) return `"${clip(query)}"`;
  const entity = pick("entity");
  if (entity) return `entity: ${entity}`;
  const wing = pick("wing");
  const room = pick("room");
  if (wing || room) {
    return [wing && `wing:${wing}`, room && `room:${room}`].filter(Boolean).join(" ");
  }

  // File tools.
  const file = pick("file_path");
  if (file) return file.split("/").slice(-2).join("/");
  const pattern = pick("pattern");
  if (pattern) return `/${clip(pattern, 40)}/`;
  const path = pick("path");
  if (path) return path.split("/").slice(-2).join("/");

  // Fallback: first non-empty string value.
  for (const [k, v] of Object.entries(input)) {
    if (typeof v === "string" && v.length > 0) {
      return `${k}: ${clip(v, 40)}`;
    }
  }
  return "";
}
