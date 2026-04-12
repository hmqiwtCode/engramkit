"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { chunks as chunksApi } from "@/lib/api";
import { StatCard } from "@/components/shared/stat-card";
import { Badge } from "@/components/shared/badge";
import type { Chunk } from "@/lib/types";

export default function ChunkDetailPage({ vaultId, hash }: { vaultId: string; hash: string }) {
  const [chunk, setChunk] = useState<Chunk | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    chunksApi
      .get(vaultId, hash)
      .then((data) => setChunk(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [vaultId, hash]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-4 h-4 border-2 border-gray-700 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !chunk) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-2">
        <p className="text-sm text-red-400 font-mono">Failed to load chunk</p>
        <p className="text-xs text-gray-600 font-mono">{error}</p>
      </div>
    );
  }

  const metadataRows = [
    { label: "Content Hash", value: chunk.content_hash, mono: true, breakAll: true },
    { label: "File Path", value: chunk.file_path || "-", mono: true, breakAll: true },
    { label: "File Hash", value: chunk.file_hash || "-", mono: true },
    { label: "Wing", badge: true },
    { label: "Room", value: chunk.room, mono: true },
    { label: "Added By", value: chunk.added_by || "-", mono: true },
    { label: "Git Commit", value: chunk.git_commit || "-", mono: true },
    { label: "Git Branch", value: chunk.git_branch || "-", mono: true },
    { label: "Created", value: new Date(chunk.created_at).toLocaleString(), mono: true },
    { label: "Updated", value: new Date(chunk.updated_at).toLocaleString(), mono: true },
  ];

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
          <Link href={`/vaults/${vaultId}/chunks`} className="text-gray-500 hover:text-gray-300 transition-colors">
            Chunks
          </Link>
          <span className="text-gray-700">/</span>
          <span className="text-gray-200 font-mono">{hash.slice(0, 12)}...</span>
        </div>
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold tracking-tight text-gray-100">Chunk Detail</h1>
          {chunk.is_stale && <Badge variant="stale">stale</Badge>}
          {chunk.is_secret && <Badge variant="secret">secret</Badge>}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Importance" value={chunk.importance} color="blue" />
        <StatCard label="Access Count" value={chunk.access_count} color="gray" />
        <StatCard label="Generation" value={chunk.generation} color="gray" />
        <StatCard
          label="Status"
          value={chunk.is_stale ? "Stale" : chunk.is_secret ? "Secret" : "Active"}
          color={chunk.is_stale ? "yellow" : chunk.is_secret ? "red" : "blue"}
        />
      </div>

      {/* Metadata -- two-column grid */}
      <div className="bg-[#111] border border-white/[0.06] rounded-lg overflow-hidden">
        <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 divide-white/[0.04]">
          {/* Left column */}
          <div className="divide-y divide-white/[0.04]">
            <div className="flex px-4 py-3">
              <span className="text-[11px] uppercase tracking-wider text-gray-500 font-medium w-32 flex-shrink-0 pt-0.5">Content Hash</span>
              <span className="font-mono text-gray-300 text-sm break-all">{chunk.content_hash}</span>
            </div>
            <div className="flex px-4 py-3">
              <span className="text-[11px] uppercase tracking-wider text-gray-500 font-medium w-32 flex-shrink-0 pt-0.5">File Path</span>
              <span className="font-mono text-gray-300 text-sm break-all">{chunk.file_path || "-"}</span>
            </div>
            <div className="flex px-4 py-3">
              <span className="text-[11px] uppercase tracking-wider text-gray-500 font-medium w-32 flex-shrink-0 pt-0.5">File Hash</span>
              <span className="font-mono text-gray-400 text-sm">{chunk.file_hash || "-"}</span>
            </div>
            <div className="flex items-center px-4 py-3">
              <span className="text-[11px] uppercase tracking-wider text-gray-500 font-medium w-32 flex-shrink-0">Wing</span>
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
            </div>
            <div className="flex px-4 py-3">
              <span className="text-[11px] uppercase tracking-wider text-gray-500 font-medium w-32 flex-shrink-0 pt-0.5">Room</span>
              <span className="font-mono text-gray-300 text-sm">{chunk.room}</span>
            </div>
            <div className="flex items-center px-4 py-3">
              <span className="text-[11px] uppercase tracking-wider text-gray-500 font-medium w-32 flex-shrink-0">Flags</span>
              <div className="flex gap-2">
                {chunk.is_stale ? <Badge variant="stale">stale</Badge> : null}
                {chunk.is_secret ? <Badge variant="secret">secret</Badge> : null}
                {!chunk.is_stale && !chunk.is_secret && (
                  <span className="text-xs text-gray-600">none</span>
                )}
              </div>
            </div>
          </div>

          {/* Right column */}
          <div className="divide-y divide-white/[0.04] md:border-l md:border-white/[0.04]">
            <div className="flex px-4 py-3">
              <span className="text-[11px] uppercase tracking-wider text-gray-500 font-medium w-32 flex-shrink-0 pt-0.5">Added By</span>
              <span className="font-mono text-gray-400 text-sm">{chunk.added_by || "-"}</span>
            </div>
            <div className="flex px-4 py-3">
              <span className="text-[11px] uppercase tracking-wider text-gray-500 font-medium w-32 flex-shrink-0 pt-0.5">Git Commit</span>
              <span className="font-mono text-gray-400 text-sm">{chunk.git_commit || "-"}</span>
            </div>
            <div className="flex px-4 py-3">
              <span className="text-[11px] uppercase tracking-wider text-gray-500 font-medium w-32 flex-shrink-0 pt-0.5">Git Branch</span>
              <span className="font-mono text-gray-400 text-sm">{chunk.git_branch || "-"}</span>
            </div>
            <div className="flex px-4 py-3">
              <span className="text-[11px] uppercase tracking-wider text-gray-500 font-medium w-32 flex-shrink-0 pt-0.5">Created</span>
              <span className="font-mono text-gray-400 text-sm">{new Date(chunk.created_at).toLocaleString()}</span>
            </div>
            <div className="flex px-4 py-3">
              <span className="text-[11px] uppercase tracking-wider text-gray-500 font-medium w-32 flex-shrink-0 pt-0.5">Updated</span>
              <span className="font-mono text-gray-400 text-sm">{new Date(chunk.updated_at).toLocaleString()}</span>
            </div>
            {chunk.last_accessed && (
              <div className="flex px-4 py-3">
                <span className="text-[11px] uppercase tracking-wider text-gray-500 font-medium w-32 flex-shrink-0 pt-0.5">Last Accessed</span>
                <span className="font-mono text-gray-400 text-sm">{new Date(chunk.last_accessed).toLocaleString()}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div>
        <h2 className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-3">Content</h2>
        <pre className="bg-[#111] border border-white/[0.06] rounded-lg p-5 text-sm text-gray-300 leading-relaxed whitespace-pre-wrap break-words font-mono overflow-x-auto">
          {chunk.content}
        </pre>
      </div>
    </div>
  );
}
