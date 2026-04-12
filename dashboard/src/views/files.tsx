"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { files as filesApi } from "@/lib/api";
import { Badge } from "@/components/shared/badge";
import type { VaultFile } from "@/lib/types";

export default function FilesPage({ vaultId }: { vaultId: string }) {
  const [fileList, setFileList] = useState<VaultFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    filesApi
      .list(vaultId)
      .then((data) => setFileList(data))
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

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-2">
        <p className="text-sm text-red-400 font-mono">Failed to load files</p>
        <p className="text-xs text-gray-600 font-mono">{error}</p>
      </div>
    );
  }

  const activeFiles = fileList.filter((f) => !f.is_deleted);
  const deletedFiles = fileList.filter((f) => f.is_deleted);

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div>
        <div className="flex items-center gap-2 text-sm mb-4">
          <Link href="/vaults" className="text-gray-500 hover:text-gray-300 transition-colors">Vaults</Link>
          <span className="text-gray-700">/</span>
          <Link href={`/vaults/${vaultId}`} className="text-gray-500 hover:text-gray-300 transition-colors font-mono">
            {vaultId}
          </Link>
          <span className="text-gray-700">/</span>
          <span className="text-gray-200">Files</span>
        </div>
        <h1 className="text-xl font-semibold tracking-tight text-gray-100">Files</h1>
        <p className="text-sm text-gray-500 mt-1">
          {activeFiles.length} active, {deletedFiles.length} deleted
        </p>
      </div>

      {/* Table */}
      {fileList.length === 0 ? (
        <div className="border border-dashed border-white/[0.06] rounded-lg py-12 text-center text-gray-600 text-sm">
          No files tracked in this vault.
        </div>
      ) : (
        <div className="bg-[#111] border border-white/[0.06] rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.06]">
                <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">File Path</th>
                <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">File Hash</th>
                <th className="text-right px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Chunks</th>
                <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Last Mined</th>
                <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Last Commit</th>
                <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {fileList.map((file) => (
                <tr key={file.file_path} className="hover:bg-white/[0.02] transition-colors">
                  <td className="px-4 py-3 font-mono text-gray-300 text-sm truncate max-w-[250px]" title={file.file_path}>
                    {file.file_path}
                  </td>
                  <td className="px-4 py-3 font-mono text-gray-500 text-sm">
                    {file.file_hash ? file.file_hash.slice(0, 12) + "..." : "-"}
                  </td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums text-gray-400 text-sm">
                    {file.chunk_count}
                  </td>
                  <td className="px-4 py-3 text-[11px] text-gray-600 font-mono whitespace-nowrap">
                    {file.last_mined_at
                      ? new Date(file.last_mined_at).toLocaleDateString()
                      : "-"}
                  </td>
                  <td className="px-4 py-3 font-mono text-gray-600 text-sm">
                    {file.last_commit ? file.last_commit.slice(0, 8) : "-"}
                  </td>
                  <td className="px-4 py-3">
                    {file.is_deleted ? (
                      <Badge variant="stale">deleted</Badge>
                    ) : (
                      <Badge variant="semantic">active</Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
