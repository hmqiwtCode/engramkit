"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { vaults as vaultsApi } from "@/lib/api";
import { StatCard } from "@/components/shared/stat-card";
import { Badge } from "@/components/shared/badge";
import type { VaultSummary } from "@/lib/types";

export default function VaultDetailPage({ vaultId }: { vaultId: string }) {
  const [vault, setVault] = useState<VaultSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    vaultsApi
      .get(vaultId)
      .then((data) => setVault(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [vaultId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-4 h-4 border-2 border-gray-700 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !vault) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-2">
        <p className="text-sm text-red-400 font-mono">Failed to load vault</p>
        <p className="text-xs text-gray-600 font-mono">{error}</p>
      </div>
    );
  }

  const wingRooms = vault.wing_rooms || {};
  const wings = Object.keys(wingRooms);

  const quickActions = [
    { label: "Chunks", href: `/vaults/${vaultId}/chunks`, desc: "Browse all chunks" },
    { label: "Files", href: `/vaults/${vaultId}/files`, desc: "View tracked files" },
    { label: "Knowledge Graph", href: `/vaults/${vaultId}/kg`, desc: "Entities & facts" },
    { label: "Mine", href: `/vaults/${vaultId}/mine`, desc: "Run mining", primary: true },
    { label: "GC", href: `/vaults/${vaultId}/gc`, desc: "Garbage collection" },
  ];

  return (
    <div className="space-y-8">
      {/* Breadcrumb */}
      <div>
        <div className="flex items-center gap-2 text-sm mb-4">
          <Link href="/vaults" className="text-gray-500 hover:text-gray-300 transition-colors">
            Vaults
          </Link>
          <span className="text-gray-700">/</span>
          <span className="text-gray-200">{vault.repo_path?.split("/").pop() || vaultId}</span>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-xl font-semibold tracking-tight text-gray-100">
            {vault.repo_path?.split("/").pop() || vaultId}
          </h1>
          {(vault as any).git_branch && (
            <span className="inline-flex items-center gap-1.5 bg-gray-800 border border-gray-700 rounded-full px-3 py-1 text-xs font-mono text-gray-300">
              {(vault as any).git_branch}
            </span>
          )}
          {(vault as any).git_commit && (
            <span className="inline-flex items-center bg-gray-800 border border-gray-700 rounded-full px-3 py-1 text-xs font-mono text-gray-500">
              {(vault as any).git_commit?.slice(0, 7)}
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500 mt-1 font-mono">{vault.repo_path}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        <StatCard label="Chunks" value={vault.total_chunks.toLocaleString()} color="blue" />
        <StatCard label="Files" value={vault.total_files.toLocaleString()} color="blue" />
        <StatCard label="Stale" value={vault.stale_chunks.toLocaleString()} color={vault.stale_chunks > 0 ? "yellow" : "gray"} />
        <StatCard label="Secrets" value={vault.secret_chunks.toLocaleString()} color={vault.secret_chunks > 0 ? "red" : "gray"} />
        <StatCard label="Generation" value={vault.generation} color="gray" />
      </div>

      {/* Quick Actions */}
      <div className="flex items-center gap-2">
        {quickActions.map((action) => (
          <Link
            key={action.href}
            href={action.href}
            className={`inline-flex items-center px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              action.primary
                ? "bg-blue-600 hover:bg-blue-500 text-white"
                : "bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 hover:border-gray-600"
            }`}
          >
            {action.label}
          </Link>
        ))}
      </div>

      {/* Wing / Room Tree */}
      {wings.length > 0 && (
        <div>
          <h3 className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-3">
            Wings & Rooms
          </h3>
          <div className="space-y-3">
            {wings.map((wing) => {
              const rooms = wingRooms[wing] || {};
              const roomNames = Object.keys(rooms);
              return (
                <div key={wing} className="rounded-lg border border-white/[0.06] overflow-hidden">
                  <div className="bg-white/[0.02] px-4 py-2.5 border-b border-white/[0.04]">
                    <span className="text-xs font-medium text-blue-400 uppercase tracking-wider">{wing}</span>
                  </div>
                  <div className="p-3 flex flex-wrap gap-2">
                    {roomNames.map((room) => (
                      <div key={room} className="inline-flex items-center gap-2 bg-[#111] border border-white/[0.06] rounded-md px-3 py-1.5">
                        <span className="text-xs text-gray-400">{room}</span>
                        <span className="text-xs font-mono font-medium text-gray-200 tabular-nums">{rooms[room]}</span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
