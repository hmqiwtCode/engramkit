"use client";

import { useState } from "react";
import Link from "next/link";
import { mining } from "@/lib/api";
import { StatCard } from "@/components/shared/stat-card";
import type { MineStats } from "@/lib/types";

export default function MinePage({ vaultId }: { vaultId: string }) {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<MineStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Mining options
  const [forceRemap, setForceRemap] = useState(false);
  const [includeHidden, setIncludeHidden] = useState(false);

  const handleMine = async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const data = await mining.start(vaultId, {
        force_remap: forceRemap,
        include_hidden: includeHidden,
      });
      setResult(data);
    } catch (err: any) {
      setError(err.message);
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
          <span className="text-gray-200">Mine</span>
        </div>
        <h1 className="text-xl font-semibold tracking-tight text-gray-100">Mine</h1>
        <p className="text-sm text-gray-500 mt-1">Scan and index repository files</p>
      </div>

      {/* Controls */}
      <div className="bg-[#111] border border-white/[0.06] rounded-lg p-5">
        <h2 className="text-sm font-medium text-gray-300 mb-4">Run Mining</h2>
        <div className="flex items-end gap-4 flex-wrap">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={forceRemap}
              onChange={(e) => setForceRemap(e.target.checked)}
              className="rounded border-white/[0.1] bg-[#0a0a0a] text-blue-500 focus:ring-blue-500/30"
            />
            <span className="text-sm text-gray-400">Force re-map all files</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={includeHidden}
              onChange={(e) => setIncludeHidden(e.target.checked)}
              className="rounded border-white/[0.1] bg-[#0a0a0a] text-blue-500 focus:ring-blue-500/30"
            />
            <span className="text-sm text-gray-400">Include hidden files</span>
          </label>
          <button
            onClick={handleMine}
            disabled={running}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {running ? (
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 border-2 border-blue-300 border-t-white rounded-full animate-spin" />
                Mining...
              </span>
            ) : "Start Mining"}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/5 border border-red-500/10 rounded-lg p-4">
          <p className="text-sm text-red-400 font-mono">{error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6">
          <h2 className="text-[11px] font-medium text-gray-500 uppercase tracking-wider">
            Mining Results
          </h2>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard label="Files Scanned" value={result.files_scanned} color="blue" />
            <StatCard label="Files Processed" value={result.files_processed} color="blue" />
            <StatCard label="Files Skipped" value={result.files_skipped} color="gray" />
            <StatCard label="Files Deleted" value={result.files_deleted} color="yellow" />
            <StatCard label="Chunks Added" value={result.chunks_added} color="blue" />
            <StatCard label="Chunks Updated" value={result.chunks_updated} color="gray" />
            <StatCard label="Chunks Stale" value={result.chunks_stale} color="yellow" />
            <StatCard label="Secrets Found" value={result.secrets_found} color="red" />
          </div>

          {/* Raw JSON */}
          <div>
            <button
              onClick={() => {
                const el = document.getElementById("mine-raw-json");
                if (el) el.classList.toggle("hidden");
              }}
              className="text-[11px] text-gray-600 hover:text-gray-400 font-mono transition-colors"
            >
              Toggle raw JSON
            </button>
            <pre
              id="mine-raw-json"
              className="hidden mt-2 bg-[#0a0a0a] border border-white/[0.04] rounded-lg p-4 text-xs text-gray-400 font-mono leading-relaxed overflow-x-auto"
            >
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!result && !error && !running && (
        <div className="border border-dashed border-white/[0.06] rounded-lg py-12 text-center text-gray-600 text-sm">
          Click &ldquo;Start Mining&rdquo; to scan and index the repository.
        </div>
      )}
    </div>
  );
}
