"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { gc as gcApi } from "@/lib/api";
import { Badge } from "@/components/shared/badge";
import type { GCLogEntry } from "@/lib/types";

export default function GCPage({ vaultId }: { vaultId: string }) {
  const [log, setLog] = useState<GCLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // GC run controls
  const [retentionDays, setRetentionDays] = useState(30);
  const [dryRun, setDryRun] = useState(true);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<any>(null);
  const [runError, setRunError] = useState<string | null>(null);

  const fetchLog = () => {
    setLoading(true);
    gcApi
      .log(vaultId)
      .then((data) => setLog(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchLog();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vaultId]);

  const handleRun = async () => {
    setRunning(true);
    setRunError(null);
    setRunResult(null);
    try {
      const result = await gcApi.run(vaultId, retentionDays, dryRun);
      setRunResult(result);
      // Refresh log after GC run
      fetchLog();
    } catch (err: any) {
      setRunError(err.message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Breadcrumb */}
      <div>
        <div className="flex items-center gap-2 text-sm mb-4">
          <Link href="/vaults" className="text-gray-500 hover:text-gray-300 transition-colors">Vaults</Link>
          <span className="text-gray-700">/</span>
          <Link href={`/vaults/${vaultId}`} className="text-gray-500 hover:text-gray-300 transition-colors font-mono">
            {vaultId}
          </Link>
          <span className="text-gray-700">/</span>
          <span className="text-gray-200">GC</span>
        </div>
        <h1 className="text-xl font-semibold tracking-tight text-gray-100">Garbage Collection</h1>
        <p className="text-sm text-gray-500 mt-1">Clean up stale and unused chunks</p>
      </div>

      {/* Controls */}
      <div className="bg-[#111] border border-white/[0.06] rounded-lg p-5">
        <h2 className="text-sm font-medium text-gray-300 mb-4">Run GC</h2>
        <div className="flex items-end gap-4 flex-wrap">
          <div>
            <label className="block text-[11px] text-gray-500 uppercase tracking-wider font-medium mb-1.5">
              Retention Days
            </label>
            <input
              type="number"
              min={1}
              value={retentionDays}
              onChange={(e) => setRetentionDays(Number(e.target.value))}
              className="w-24 bg-[#111] border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 font-mono focus:border-blue-500/50 focus:outline-none transition-colors"
            />
          </div>
          <div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={dryRun}
                onChange={(e) => setDryRun(e.target.checked)}
                className="rounded border-white/[0.1] bg-[#0a0a0a] text-blue-500 focus:ring-blue-500/30"
              />
              <span className="text-sm text-gray-400">Dry run</span>
            </label>
          </div>
          <button
            onClick={handleRun}
            disabled={running}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              dryRun
                ? "bg-blue-600 text-white hover:bg-blue-500"
                : "bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/15"
            } disabled:opacity-40 disabled:cursor-not-allowed`}
          >
            {running ? (
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 border-2 border-gray-400 border-t-white rounded-full animate-spin" />
                Running...
              </span>
            ) : dryRun ? "Preview" : "Run GC"}
          </button>
        </div>

        {/* Run result */}
        {runResult && (
          <div className="mt-4 bg-[#0a0a0a] border border-white/[0.04] rounded-lg p-4">
            <p className="text-[11px] text-gray-500 uppercase tracking-wider font-medium mb-2">Result</p>
            <pre className="text-xs text-gray-300 font-mono leading-relaxed overflow-x-auto">
              {JSON.stringify(runResult, null, 2)}
            </pre>
          </div>
        )}

        {runError && (
          <div className="mt-4 bg-red-500/5 border border-red-500/10 rounded-lg p-3">
            <p className="text-sm text-red-400 font-mono">{runError}</p>
          </div>
        )}
      </div>

      {/* Log */}
      <div>
        <h2 className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-4">
          GC Log
        </h2>

        {error && (
          <div className="bg-red-500/5 border border-red-500/10 rounded-lg p-4 mb-4">
            <p className="text-sm text-red-400 font-mono">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-4 h-4 border-2 border-gray-700 border-t-blue-500 rounded-full animate-spin" />
          </div>
        ) : log.length === 0 ? (
          <div className="border border-dashed border-white/[0.06] rounded-lg py-12 text-center text-gray-600 text-sm">
            No GC entries yet.
          </div>
        ) : (
          <div className="bg-[#111] border border-white/[0.06] rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">ID</th>
                  <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Action</th>
                  <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Hash</th>
                  <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">File</th>
                  <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Reason</th>
                  <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {log.map((entry) => (
                  <tr key={entry.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3 font-mono text-gray-500 tabular-nums text-sm">{entry.id}</td>
                    <td className="px-4 py-3">
                      <Badge
                        variant={
                          entry.action === "delete"
                            ? "stale"
                            : entry.action === "invalidate"
                              ? "secret"
                              : "default"
                        }
                      >
                        {entry.action}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 font-mono text-gray-400 text-sm">
                      {entry.content_hash ? entry.content_hash.slice(0, 12) + "..." : "-"}
                    </td>
                    <td className="px-4 py-3 font-mono text-gray-500 text-sm truncate max-w-[150px]">
                      {entry.file_path || "-"}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{entry.reason}</td>
                    <td className="px-4 py-3 text-[11px] text-gray-600 font-mono whitespace-nowrap">
                      {new Date(entry.performed_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
