"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { vaults as vaultsApi, search as searchApi } from "@/lib/api";
import { Badge } from "@/components/shared/badge";
import type { SearchResult, VaultSummary } from "@/lib/types";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  // Vault list
  const [vaultList, setVaultList] = useState<VaultSummary[]>([]);
  const [selectedVault, setSelectedVault] = useState("");

  // Filters
  const [nResults, setNResults] = useState(10);
  const [wingFilter, setWingFilter] = useState("");
  const [roomFilter, setRoomFilter] = useState("");

  useEffect(() => {
    vaultsApi.list().then(setVaultList).catch(() => {});
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setSearched(true);

    try {
      const data = selectedVault
        ? await searchApi.inVault(selectedVault, query.trim(), nResults, wingFilter || undefined, roomFilter || undefined)
        : await searchApi.global(query.trim(), nResults, wingFilter || undefined, roomFilter || undefined);
      setResults(Array.isArray(data) ? data : data.results || []);
    } catch (err: any) {
      setError(err.message);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-semibold tracking-tight text-gray-100">Search</h2>
        <p className="text-sm text-gray-400 mt-1">Semantic search across all vaults</p>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch}>
        <div className="bg-[#111] border border-white/[0.06] rounded-xl p-1.5 focus-within:border-blue-500/30 transition-colors">
          <div className="flex items-center gap-2">
            {/* Search Icon */}
            <div className="pl-3 flex-shrink-0">
              <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
              </svg>
            </div>

            {/* Input */}
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search chunks across all vaults..."
              className="flex-1 bg-transparent py-2.5 text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none font-mono"
            />

            {/* Result Count */}
            <select
              value={nResults}
              onChange={(e) => setNResults(Number(e.target.value))}
              className="bg-[#0a0a0a] border border-white/[0.06] rounded-lg px-2 py-1.5 text-xs text-gray-400 font-mono focus:outline-none focus:border-blue-500/50 appearance-none cursor-pointer"
            >
              {[5, 10, 20, 30, 50].map((n) => (
                <option key={n} value={n}>{n} results</option>
              ))}
            </select>

            {/* Search Button */}
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-blue-600 flex items-center gap-2"
            >
              {loading ? (
                <div className="w-3.5 h-3.5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
                </svg>
              )}
              {loading ? "Searching" : "Search"}
            </button>
          </div>
        </div>

        {/* Filters Row */}
        <div className="flex items-center gap-4 mt-3 px-1">
          <div className="flex items-center gap-2">
            <label className="text-[11px] text-gray-500 uppercase tracking-wider font-medium">Vault</label>
            <select
              value={selectedVault}
              onChange={(e) => setSelectedVault(e.target.value)}
              className="appearance-none bg-[#111] border border-white/[0.06] rounded-lg px-2.5 py-1.5 text-xs text-gray-300 font-mono focus:border-blue-500/50 focus:outline-none cursor-pointer"
            >
              <option value="">All vaults</option>
              {vaultList.map((v) => (
                <option key={v.vault_id} value={v.vault_id}>
                  {v.repo_path.split("/").pop()} ({v.total_chunks})
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-[11px] text-gray-500 uppercase tracking-wider font-medium">Wing</label>
            <input
              type="text"
              value={wingFilter}
              onChange={(e) => setWingFilter(e.target.value)}
              placeholder="any"
              className="w-24 bg-[#111] border border-white/[0.06] rounded-lg px-2.5 py-1.5 text-xs text-gray-300 font-mono placeholder:text-gray-700 focus:border-blue-500/50 focus:outline-none"
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-[11px] text-gray-500 uppercase tracking-wider font-medium">Room</label>
            <input
              type="text"
              value={roomFilter}
              onChange={(e) => setRoomFilter(e.target.value)}
              placeholder="any"
              className="w-24 bg-[#111] border border-white/[0.06] rounded-lg px-2.5 py-1.5 text-xs text-gray-300 font-mono placeholder:text-gray-700 focus:border-blue-500/50 focus:outline-none"
            />
          </div>
        </div>
      </form>

      {/* Error */}
      {error && (
        <div className="bg-red-500/5 border border-red-500/10 rounded-lg px-4 py-3 flex items-center gap-3">
          <svg className="w-4 h-4 text-red-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
          </svg>
          <p className="text-sm text-red-400 font-mono">{error}</p>
        </div>
      )}

      {/* Results */}
      {searched && !loading && !error && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-[11px] text-gray-500 uppercase tracking-wider font-medium font-mono">
              {results.length} result{results.length !== 1 ? "s" : ""}
            </p>
          </div>

          {results.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <div className="w-12 h-12 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center justify-center">
                <svg className="w-6 h-6 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
                </svg>
              </div>
              <p className="text-sm text-gray-400">No results found</p>
              <p className="text-xs text-gray-600 font-mono">No matches for &ldquo;{query}&rdquo;</p>
            </div>
          ) : (
            <div className="space-y-3">
              {results.map((result, i) => (
                <div
                  key={`${result.content_hash}-${i}`}
                  className="bg-[#111] border border-white/[0.06] rounded-lg hover:border-white/[0.12] transition-all duration-200 overflow-hidden"
                >
                  {/* Header row */}
                  <div className="flex items-center justify-between gap-3 px-4 pt-4 pb-2">
                    <div className="flex items-center gap-2 min-w-0">
                      {result.file_path && (
                        <p className="text-xs text-blue-400 font-mono truncate">
                          {result.file_path}
                        </p>
                      )}
                      {result.vault_id && (
                        <Link
                          href={`/vaults/${result.vault_id}`}
                          className="text-[10px] text-gray-600 hover:text-gray-400 font-mono transition-colors flex-shrink-0"
                        >
                          {result.vault_id}
                        </Link>
                      )}
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0">
                      <Badge
                        variant={
                          result.wing === "semantic"
                            ? "semantic"
                            : result.wing === "lexical"
                              ? "lexical"
                              : "default"
                        }
                      >
                        {result.wing}
                      </Badge>
                      {result.room && <Badge>{result.room}</Badge>}
                    </div>
                  </div>

                  {/* Score meter */}
                  <div className="px-4 pb-2">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-px bg-white/[0.04] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500/40 rounded-full"
                          style={{ width: `${Math.min((result.score || 0) * 100, 100)}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-gray-500 font-mono tabular-nums flex-shrink-0">
                        {result.score?.toFixed(4)}
                      </span>
                    </div>
                  </div>

                  {/* Content */}
                  <div className="mx-4 mb-4 bg-[#0a0a0a] border border-white/[0.04] rounded-md p-3">
                    <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap line-clamp-4 font-mono">
                      {result.content}
                    </p>
                  </div>

                  {/* Footer */}
                  <div className="flex items-center justify-between px-4 py-2.5 border-t border-white/[0.04] bg-white/[0.01]">
                    <div className="flex items-center gap-3">
                      {result.importance != null && (
                        <span className="text-[10px] text-gray-500 font-mono">
                          importance {result.importance}
                        </span>
                      )}
                      {result.created_at && (
                        <span className="text-[10px] text-gray-600 font-mono">
                          {new Date(result.created_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    {result.vault_id && (
                      <Link
                        href={`/vaults/${result.vault_id}/chunks/${result.content_hash}`}
                        className="text-[11px] text-blue-400/70 hover:text-blue-400 font-mono transition-colors flex items-center gap-1"
                      >
                        View chunk
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                        </svg>
                      </Link>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Loading overlay for results */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-16 gap-4">
          <div className="relative w-8 h-8">
            <div className="absolute inset-0 rounded-full border-2 border-white/[0.06]" />
            <div className="absolute inset-0 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
          </div>
          <p className="text-xs text-gray-500 font-mono">Searching...</p>
        </div>
      )}
    </div>
  );
}
