"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { chunks as chunksApi } from "@/lib/api";
import { Badge } from "@/components/shared/badge";
import type { Chunk, PaginatedChunks } from "@/lib/types";

export default function ChunksPage({ vaultId }: { vaultId: string }) {
  const [data, setData] = useState<PaginatedChunks | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination & filters
  const [page, setPage] = useState(1);
  const [perPage] = useState(20);
  const [wingFilter, setWingFilter] = useState("");
  const [roomFilter, setRoomFilter] = useState("");
  const [staleFilter, setStaleFilter] = useState<"" | "0" | "1">("");

  const fetchChunks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, any> = { page, per_page: perPage };
      if (wingFilter) params.wing = wingFilter;
      if (roomFilter) params.room = roomFilter;
      if (staleFilter) params.is_stale = staleFilter;
      const result = await chunksApi.list(vaultId, params);
      setData(result);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [vaultId, page, perPage, wingFilter, roomFilter, staleFilter]);

  useEffect(() => {
    fetchChunks();
  }, [fetchChunks]);

  const chunkList: Chunk[] = data?.chunks || [];
  const totalPages = data?.pages || 1;
  const total = data?.total || 0;

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
          <span className="text-gray-200">Chunks</span>
        </div>
        <h1 className="text-xl font-semibold tracking-tight text-gray-100">Chunks</h1>
        <p className="text-sm text-gray-500 mt-1">
          {total.toLocaleString()} chunk{total !== 1 ? "s" : ""} total
        </p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <label className="text-[11px] text-gray-500 uppercase tracking-wider font-medium">Wing</label>
          <input
            type="text"
            value={wingFilter}
            onChange={(e) => { setWingFilter(e.target.value); setPage(1); }}
            placeholder="any"
            className="w-24 bg-[#111] border border-white/[0.06] rounded-lg px-2.5 py-1.5 text-xs text-gray-300 font-mono placeholder:text-gray-700 focus:border-blue-500/50 focus:outline-none transition-colors"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-[11px] text-gray-500 uppercase tracking-wider font-medium">Room</label>
          <input
            type="text"
            value={roomFilter}
            onChange={(e) => { setRoomFilter(e.target.value); setPage(1); }}
            placeholder="any"
            className="w-24 bg-[#111] border border-white/[0.06] rounded-lg px-2.5 py-1.5 text-xs text-gray-300 font-mono placeholder:text-gray-700 focus:border-blue-500/50 focus:outline-none transition-colors"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-[11px] text-gray-500 uppercase tracking-wider font-medium">Stale</label>
          <select
            value={staleFilter}
            onChange={(e) => { setStaleFilter(e.target.value as "" | "0" | "1"); setPage(1); }}
            className="bg-[#111] border border-white/[0.06] rounded-lg px-2.5 py-1.5 text-xs text-gray-300 font-mono focus:border-blue-500/50 focus:outline-none transition-colors"
          >
            <option value="">any</option>
            <option value="0">fresh</option>
            <option value="1">stale</option>
          </select>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/5 border border-red-500/10 rounded-lg p-4">
          <p className="text-sm text-red-400 font-mono">{error}</p>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-4 h-4 border-2 border-gray-700 border-t-blue-500 rounded-full animate-spin" />
        </div>
      ) : chunkList.length === 0 ? (
        <div className="border border-dashed border-white/[0.06] rounded-lg py-12 text-center text-gray-600 text-sm">
          No chunks found.
        </div>
      ) : (
        <div className="bg-[#111] border border-white/[0.06] rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.06]">
                <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Hash</th>
                <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Wing</th>
                <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Room</th>
                <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">File</th>
                <th className="text-right px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Imp</th>
                <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Status</th>
                <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {chunkList.map((chunk) => (
                <tr key={chunk.content_hash} className="hover:bg-white/[0.02] transition-colors cursor-pointer group">
                  <td className="px-4 py-3">
                    <Link
                      href={`/vaults/${vaultId}/chunks/${chunk.content_hash}`}
                      className="text-blue-400 hover:text-blue-300 font-mono text-sm transition-colors"
                    >
                      {chunk.content_hash.slice(0, 12)}...
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      variant={
                        chunk.wing === "semantic"
                          ? "semantic"
                          : chunk.wing === "lexical"
                            ? "lexical"
                            : "default"
                      }
                    >
                      {chunk.wing}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 font-mono text-gray-500 text-sm">{chunk.room}</td>
                  <td className="px-4 py-3 font-mono text-gray-500 text-sm truncate max-w-[150px]">
                    {chunk.file_path || "-"}
                  </td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums text-gray-400 text-sm">
                    {chunk.importance}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      {chunk.is_stale ? <Badge variant="stale">stale</Badge> : null}
                      {chunk.is_secret ? <Badge variant="secret">secret</Badge> : null}
                      {!chunk.is_stale && !chunk.is_secret && (
                        <span className="text-[11px] text-gray-700">-</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-[11px] text-gray-600 font-mono whitespace-nowrap">
                    {new Date(chunk.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-600 font-mono tabular-nums">
            Page {page} of {totalPages}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1.5 text-xs bg-white/[0.02] border border-white/[0.06] rounded-lg text-gray-400 hover:text-gray-200 hover:border-white/[0.1] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Prev
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1.5 text-xs bg-white/[0.02] border border-white/[0.06] rounded-lg text-gray-400 hover:text-gray-200 hover:border-white/[0.1] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
