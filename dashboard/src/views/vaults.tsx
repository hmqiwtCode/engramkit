"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { vaults as vaultsApi } from "@/lib/api";
import { Badge } from "@/components/shared/badge";
import type { VaultSummary } from "@/lib/types";

export default function VaultsPage() {
  const [vaultList, setVaultList] = useState<VaultSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    vaultsApi
      .list()
      .then((data) => setVaultList(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-4 h-4 border-2 border-gray-700 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-2">
        <p className="text-sm text-red-400 font-mono">Failed to load vaults</p>
        <p className="text-xs text-gray-600 font-mono">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-gray-100">Vaults</h1>
          <p className="text-sm text-gray-500 mt-1">
            {vaultList.length} vault{vaultList.length !== 1 ? "s" : ""}
          </p>
        </div>
      </div>

      {/* Table */}
      {vaultList.length === 0 ? (
        <div className="border border-dashed border-white/[0.06] rounded-lg py-12 text-center text-gray-600 text-sm">
          No vaults found. Create one via the API.
        </div>
      ) : (
        <div className="bg-[#111] border border-white/[0.06] rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.06]">
                <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Vault ID</th>
                <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Repo Path</th>
                <th className="text-right px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Chunks</th>
                <th className="text-right px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Files</th>
                <th className="text-right px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Stale</th>
                <th className="text-right px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Gen</th>
                <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Wings</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {vaultList.map((vault) => {
                const wings = vault.wing_rooms ? Object.keys(vault.wing_rooms) : [];
                return (
                  <tr key={vault.vault_id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3">
                      <Link
                        href={`/vaults/${vault.vault_id}`}
                        className="text-blue-400 hover:text-blue-300 font-mono text-sm transition-colors"
                      >
                        {vault.vault_id}
                      </Link>
                    </td>
                    <td className="px-4 py-3 font-mono text-gray-500 text-sm truncate max-w-[200px]">
                      {vault.repo_path}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums text-gray-300 text-sm">
                      {vault.total_chunks.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums text-gray-300 text-sm">
                      {vault.total_files.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums text-sm">
                      {vault.stale_chunks > 0 ? (
                        <span className="text-amber-400">{vault.stale_chunks}</span>
                      ) : (
                        <span className="text-gray-700">0</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums text-gray-500 text-sm">
                      {vault.generation}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {wings.map((wing) => (
                          <Badge
                            key={wing}
                            variant={
                              wing === "semantic"
                                ? "semantic"
                                : wing === "lexical"
                                  ? "lexical"
                                  : "default"
                            }
                          >
                            {wing}
                          </Badge>
                        ))}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
