"use client";

import type { Usage } from "../types";

export function UsageStats({ usage }: { usage: Usage }) {
  const stats: Array<{ key: string; label: string } | null> = [
    usage.duration_ms > 0 ? { key: "dur", label: `${(usage.duration_ms / 1000).toFixed(1)}s` } : null,
    usage.total_cost_usd > 0 ? { key: "cost", label: `$${usage.total_cost_usd.toFixed(4)}` } : null,
    usage.input_tokens > 0 || usage.output_tokens > 0
      ? { key: "tok", label: `${usage.input_tokens + usage.output_tokens} tok` }
      : null,
    usage.cache_read_tokens > 0 ? { key: "cache", label: `${usage.cache_read_tokens} cached` } : null,
    usage.tool_calls > 0 ? { key: "tools", label: `${usage.tool_calls} tool${usage.tool_calls === 1 ? "" : "s"}` } : null,
    usage.num_turns > 1 ? { key: "turns", label: `${usage.num_turns} turns` } : null,
  ];
  const visible = stats.filter((s): s is { key: string; label: string } => s !== null);
  if (visible.length === 0) return null;

  return (
    <div className="flex items-center gap-3 mt-2 pt-2 border-t border-white/[0.04] flex-wrap">
      {visible.map((s) => (
        <span key={s.key} className="text-[10px] text-gray-600 font-mono tabular-nums">
          {s.label}
        </span>
      ))}
    </div>
  );
}
