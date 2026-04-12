"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { kg as kgApi } from "@/lib/api";
import { StatCard } from "@/components/shared/stat-card";
import { Badge } from "@/components/shared/badge";
import type { KGStats, KGEntity, KGFact } from "@/lib/types";

type Tab = "entities" | "facts" | "timeline" | "add";

export default function KGPage({ vaultId }: { vaultId: string }) {
  const [stats, setStats] = useState<KGStats | null>(null);
  const [entities, setEntities] = useState<KGEntity[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [entityFacts, setEntityFacts] = useState<KGFact[]>([]);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>("entities");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Add triple form
  const [tripleSubject, setTripleSubject] = useState("");
  const [triplePredicate, setTriplePredicate] = useState("");
  const [tripleObject, setTripleObject] = useState("");
  const [tripleConfidence, setTripleConfidence] = useState(1.0);
  const [addLoading, setAddLoading] = useState(false);
  const [addResult, setAddResult] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      kgApi.stats(vaultId).catch(() => null),
      kgApi.entities(vaultId).catch(() => []),
    ])
      .then(([s, e]) => {
        setStats(s);
        setEntities(e);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [vaultId]);

  const loadEntityFacts = async (name: string) => {
    setSelectedEntity(name);
    try {
      const data = await kgApi.entity(vaultId, name);
      setEntityFacts(Array.isArray(data) ? data : data.facts || []);
    } catch {
      setEntityFacts([]);
    }
  };

  const loadTimeline = async () => {
    try {
      const data = await kgApi.timeline(vaultId);
      setTimeline(Array.isArray(data) ? data : data.events || []);
    } catch {
      setTimeline([]);
    }
  };

  useEffect(() => {
    if (activeTab === "timeline") {
      loadTimeline();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, vaultId]);

  const handleAddTriple = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tripleSubject.trim() || !triplePredicate.trim() || !tripleObject.trim()) return;

    setAddLoading(true);
    setAddResult(null);
    try {
      await kgApi.addTriple(vaultId, {
        subject: tripleSubject.trim(),
        predicate: triplePredicate.trim(),
        object: tripleObject.trim(),
        confidence: tripleConfidence,
      });
      setAddResult("Triple added successfully");
      setTripleSubject("");
      setTriplePredicate("");
      setTripleObject("");
      setTripleConfidence(1.0);
      // Refresh entities and stats
      const [s, e] = await Promise.all([
        kgApi.stats(vaultId).catch(() => null),
        kgApi.entities(vaultId).catch(() => []),
      ]);
      setStats(s);
      setEntities(e);
    } catch (err: any) {
      setAddResult(`Error: ${err.message}`);
    } finally {
      setAddLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-4 h-4 border-2 border-gray-700 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "entities", label: "Entities" },
    { key: "facts", label: "Facts" },
    { key: "timeline", label: "Timeline" },
    { key: "add", label: "Add Triple" },
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
          <span className="text-gray-200">Knowledge Graph</span>
        </div>
        <h1 className="text-xl font-semibold tracking-tight text-gray-100">Knowledge Graph</h1>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Entities" value={stats.entities} color="blue" />
          <StatCard label="Triples" value={stats.triples} color="blue" />
          <StatCard label="Current Facts" value={stats.current_facts} color="gray" />
          <StatCard label="Expired Facts" value={stats.expired_facts} color="yellow" />
        </div>
      )}

      {/* Relationship Types */}
      {stats && stats.relationship_types && stats.relationship_types.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          <span className="text-[11px] text-gray-500 uppercase tracking-wider font-medium mr-2 self-center">
            Relationships:
          </span>
          {stats.relationship_types.map((rt) => (
            <Badge key={rt}>{rt}</Badge>
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-500/5 border border-red-500/10 rounded-lg p-4">
          <p className="text-sm text-red-400 font-mono">{error}</p>
        </div>
      )}

      {/* Pill Nav Tabs */}
      <div className="flex gap-1 bg-white/[0.02] rounded-full p-1 w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-1.5 text-sm font-medium rounded-full transition-colors ${
              activeTab === tab.key
                ? "bg-blue-600 text-white"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab: Entities */}
      {activeTab === "entities" && (
        <div>
          {entities.length === 0 ? (
            <div className="border border-dashed border-white/[0.06] rounded-lg py-12 text-center text-gray-600 text-sm">
              No entities found.
            </div>
          ) : (
            <div className="grid gap-2">
              {entities.map((entity) => (
                <button
                  key={entity.id || entity.name}
                  onClick={() => loadEntityFacts(entity.name)}
                  className={`w-full text-left bg-[#111] border rounded-lg p-4 transition-all duration-150 ${
                    selectedEntity === entity.name
                      ? "border-blue-500/30 bg-blue-500/5"
                      : "border-white/[0.06] hover:border-white/[0.1] hover:bg-white/[0.02]"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <p className="text-sm font-medium text-gray-200 font-mono">{entity.name}</p>
                      <Badge>{entity.type}</Badge>
                    </div>
                    <span className="text-[10px] text-gray-600 font-mono">
                      {new Date(entity.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab: Facts (for selected entity) */}
      {activeTab === "facts" && (
        <div>
          {!selectedEntity ? (
            <div className="border border-dashed border-white/[0.06] rounded-lg py-12 text-center text-gray-600 text-sm">
              Select an entity from the Entities tab to view its facts.
            </div>
          ) : (
            <div>
              <div className="flex items-center gap-2 mb-4">
                <span className="text-sm text-gray-400">Facts for</span>
                <Badge variant="semantic">{selectedEntity}</Badge>
              </div>
              {entityFacts.length === 0 ? (
                <div className="border border-dashed border-white/[0.06] rounded-lg py-8 text-center text-gray-600 text-sm">
                  No facts found for this entity.
                </div>
              ) : (
                <div className="bg-[#111] border border-white/[0.06] rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-white/[0.06]">
                        <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Subject</th>
                        <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Predicate</th>
                        <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Object</th>
                        <th className="text-right px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Confidence</th>
                        <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Valid From</th>
                        <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Valid To</th>
                        <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.04]">
                      {entityFacts.map((fact, i) => (
                        <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                          <td className="px-4 py-3 font-mono text-gray-300 text-sm">{fact.subject}</td>
                          <td className="px-4 py-3 font-mono text-blue-400/80 text-sm">{fact.predicate}</td>
                          <td className="px-4 py-3 font-mono text-gray-300 text-sm">{fact.object}</td>
                          <td className="px-4 py-3 font-mono text-gray-400 tabular-nums text-right text-sm">
                            {fact.confidence.toFixed(2)}
                          </td>
                          <td className="px-4 py-3 text-[11px] text-gray-600 font-mono">
                            {fact.valid_from ? new Date(fact.valid_from).toLocaleDateString() : "-"}
                          </td>
                          <td className="px-4 py-3 text-[11px] text-gray-600 font-mono">
                            {fact.valid_to ? new Date(fact.valid_to).toLocaleDateString() : "-"}
                          </td>
                          <td className="px-4 py-3">
                            {fact.current ? (
                              <Badge variant="semantic">current</Badge>
                            ) : (
                              <Badge variant="stale">expired</Badge>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab: Timeline */}
      {activeTab === "timeline" && (
        <div>
          {timeline.length === 0 ? (
            <div className="border border-dashed border-white/[0.06] rounded-lg py-12 text-center text-gray-600 text-sm">
              No timeline events found.
            </div>
          ) : (
            <div className="space-y-3">
              {timeline.map((event, i) => (
                <div
                  key={i}
                  className="bg-[#111] border border-white/[0.06] rounded-lg p-4 flex items-start gap-4 hover:bg-white/[0.02] transition-colors"
                >
                  <div className="w-2 h-2 rounded-full bg-blue-500/40 mt-1.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-mono text-gray-200">
                        {event.subject || event.entity}
                      </span>
                      <span className="text-sm text-blue-400/70 font-mono">
                        {event.predicate || event.action}
                      </span>
                      <span className="text-sm font-mono text-gray-200">
                        {event.object || event.target}
                      </span>
                    </div>
                    {event.valid_from && (
                      <p className="text-[10px] text-gray-600 font-mono mt-1">
                        {new Date(event.valid_from).toLocaleString()}
                      </p>
                    )}
                  </div>
                  {event.confidence != null && (
                    <span className="text-[10px] text-gray-600 font-mono tabular-nums flex-shrink-0">
                      {event.confidence.toFixed(2)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab: Add Triple */}
      {activeTab === "add" && (
        <form onSubmit={handleAddTriple} className="bg-[#111] border border-white/[0.06] rounded-lg p-5 space-y-4">
          <h2 className="text-sm font-medium text-gray-300">Add a New Triple</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-[11px] text-gray-500 uppercase tracking-wider font-medium mb-1.5">
                Subject
              </label>
              <input
                type="text"
                value={tripleSubject}
                onChange={(e) => setTripleSubject(e.target.value)}
                placeholder="e.g. React"
                className="w-full bg-[#111] border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 font-mono placeholder:text-gray-700 focus:border-blue-500/50 focus:outline-none transition-colors"
              />
            </div>
            <div>
              <label className="block text-[11px] text-gray-500 uppercase tracking-wider font-medium mb-1.5">
                Predicate
              </label>
              <input
                type="text"
                value={triplePredicate}
                onChange={(e) => setTriplePredicate(e.target.value)}
                placeholder="e.g. is_a"
                className="w-full bg-[#111] border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 font-mono placeholder:text-gray-700 focus:border-blue-500/50 focus:outline-none transition-colors"
              />
            </div>
            <div>
              <label className="block text-[11px] text-gray-500 uppercase tracking-wider font-medium mb-1.5">
                Object
              </label>
              <input
                type="text"
                value={tripleObject}
                onChange={(e) => setTripleObject(e.target.value)}
                placeholder="e.g. JavaScript library"
                className="w-full bg-[#111] border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 font-mono placeholder:text-gray-700 focus:border-blue-500/50 focus:outline-none transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] text-gray-500 uppercase tracking-wider font-medium mb-1.5">
              Confidence (0-1)
            </label>
            <input
              type="number"
              min={0}
              max={1}
              step={0.1}
              value={tripleConfidence}
              onChange={(e) => setTripleConfidence(Number(e.target.value))}
              className="w-24 bg-[#111] border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 font-mono focus:border-blue-500/50 focus:outline-none transition-colors"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={addLoading || !tripleSubject.trim() || !triplePredicate.trim() || !tripleObject.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {addLoading ? (
                <span className="flex items-center gap-2">
                  <span className="w-3 h-3 border-2 border-blue-300 border-t-white rounded-full animate-spin" />
                  Adding...
                </span>
              ) : "Add Triple"}
            </button>
            {addResult && (
              <p className={`text-xs font-mono ${addResult.startsWith("Error") ? "text-red-400" : "text-green-400"}`}>
                {addResult}
              </p>
            )}
          </div>
        </form>
      )}
    </div>
  );
}
