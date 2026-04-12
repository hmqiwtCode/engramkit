"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { vaults as vaultsApi } from "@/lib/api";
import { StatCard } from "@/components/shared/stat-card";
import { Badge } from "@/components/shared/badge";
import type { VaultSummary } from "@/lib/types";

export default function DashboardPage() {
  const [vaultList, setVaultList] = useState<VaultSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    vaultsApi.list().then(setVaultList).finally(() => setLoading(false));
  }, []);

  const totalChunks = vaultList.reduce((s, v) => s + v.total_chunks, 0);
  const totalFiles = vaultList.reduce((s, v) => s + v.total_files, 0);
  const totalStale = vaultList.reduce((s, v) => s + v.stale_chunks, 0);

  return (
    <div>
      {/* Page header */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-100 tracking-tight">Dashboard</h2>
        <p className="text-sm text-gray-500 mt-1">Overview of your knowledge vaults</p>
      </div>

      {/* Stats grid — 4 cards only */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-10">
        <StatCard label="Vaults" value={vaultList.length} color="blue" />
        <StatCard label="Chunks" value={totalChunks.toLocaleString()} color="blue" />
        <StatCard label="Files" value={totalFiles.toLocaleString()} color="gray" />
        <StatCard label="Stale" value={totalStale.toLocaleString()} color={totalStale > 0 ? "yellow" : "gray"} />
      </div>

      {/* Vault cards */}
      {loading ? (
        <div className="flex items-center gap-3 py-20 justify-center">
          <div className="h-4 w-4 rounded-full border-2 border-gray-700 border-t-blue-500 animate-spin" />
          <span className="text-sm text-gray-500">Loading vaults...</span>
        </div>
      ) : vaultList.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-sm font-medium text-gray-400">No vaults yet</p>
          <p className="text-xs text-gray-600 mt-2 font-mono">Run: engramkit mine /path/to/repo</p>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider">Vaults</h3>
            <span className="text-xs text-gray-600">{vaultList.length} total</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {vaultList.map((v) => (
              <Link
                key={v.vault_id}
                href={`/vaults/${v.vault_id}`}
                className="group border border-white/[0.06] rounded-lg p-5 transition-all duration-150 hover:border-white/[0.1] hover:bg-white/[0.02]"
              >
                {/* Header: repo name + Gen badge */}
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-mono text-sm font-semibold text-gray-100 truncate group-hover:text-blue-400 transition-colors duration-150">
                    {v.repo_path.split("/").pop()}
                  </h3>
                  <Badge>Gen {v.generation}</Badge>
                </div>

                {/* Repo path */}
                <p className="text-[11px] text-gray-600 truncate mb-5 font-mono">{v.repo_path}</p>

                {/* Stats: chunks / files / stale */}
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <p className="text-base font-semibold font-mono text-gray-200 tracking-tight">{v.total_chunks.toLocaleString()}</p>
                    <p className="text-[11px] text-gray-600 mt-0.5">chunks</p>
                  </div>
                  <div>
                    <p className="text-base font-semibold font-mono text-gray-200 tracking-tight">{v.total_files.toLocaleString()}</p>
                    <p className="text-[11px] text-gray-600 mt-0.5">files</p>
                  </div>
                  <div>
                    <p className={`text-base font-semibold font-mono tracking-tight ${v.stale_chunks > 0 ? "text-yellow-400" : "text-gray-200"}`}>{v.stale_chunks.toLocaleString()}</p>
                    <p className="text-[11px] text-gray-600 mt-0.5">stale</p>
                  </div>
                </div>

                {/* Wing/Room badges */}
                {v.wing_rooms && Object.keys(v.wing_rooms).length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-4 pt-4 border-t border-white/[0.04]">
                    {Object.entries(v.wing_rooms || {}).map(([wing, rooms]) =>
                      Object.keys(rooms).map((room) => (
                        <Badge key={`${wing}-${room}`}>
                          {wing}/{room}
                        </Badge>
                      ))
                    )}
                  </div>
                )}
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
