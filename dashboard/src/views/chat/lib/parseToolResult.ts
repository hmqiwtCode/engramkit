/** Try to parse an engramkit tool result (which is JSON-encoded). Returns null on non-JSON. */
export function tryParseJson(text: string | undefined): unknown {
  if (!text) return null;
  const trimmed = text.trim();
  if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) return null;
  try {
    return JSON.parse(trimmed);
  } catch {
    return null;
  }
}
