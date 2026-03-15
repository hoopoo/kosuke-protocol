import { useState, useEffect } from "react";
import {
  api,
  type TopConceptsResult,
  type GalaxyWatchResult,
  type ReflectionImpactResult,
  type DomainBalanceResult,
  type EmergingSignalsResult,
} from "@/lib/api";
import {
  Crown,
  Orbit,
  PenLine,
  BarChart3,
  Zap,
  TrendingUp,
  TrendingDown,
  Minus,
  Star,
  Loader2,
  RefreshCw,
  AlertTriangle,
} from "lucide-react";

const DOMAIN_COLORS: Record<string, string> = {
  philosophy: "#a855f7",
  technology: "#3b82f6",
  art: "#22c55e",
  science: "#06b6d4",
  urban: "#14b8a6",
  body: "#f97316",
  nature: "#84cc16",
  politics: "#ef4444",
  economics: "#eab308",
  culture: "#ec4899",
  psychology: "#8b5cf6",
  literature: "#d946ef",
  music: "#f59e0b",
  spirituality: "#6366f1",
  mathematics: "#0ea5e9",
};

type Panel = "top-concepts" | "galaxies" | "reflection-impact" | "domain-balance" | "emerging-signals";

export function ObservatoryPanel() {
  const [activePanel, setActivePanel] = useState<Panel>("top-concepts");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [topConcepts, setTopConcepts] = useState<TopConceptsResult | null>(null);
  const [galaxyWatch, setGalaxyWatch] = useState<GalaxyWatchResult | null>(null);
  const [reflectionImpact, setReflectionImpact] = useState<ReflectionImpactResult | null>(null);
  const [domainBalance, setDomainBalance] = useState<DomainBalanceResult | null>(null);
  const [emergingSignals, setEmergingSignals] = useState<EmergingSignalsResult | null>(null);

  const loadPanel = async (panel: Panel) => {
    setLoading(true);
    setError(null);
    try {
      switch (panel) {
        case "top-concepts":
          setTopConcepts(await api.getTopConcepts());
          break;
        case "galaxies":
          setGalaxyWatch(await api.getGalaxyWatch());
          break;
        case "reflection-impact":
          setReflectionImpact(await api.getReflectionImpact());
          break;
        case "domain-balance":
          setDomainBalance(await api.getDomainBalance());
          break;
        case "emerging-signals":
          setEmergingSignals(await api.getEmergingSignals());
          break;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPanel(activePanel);
  }, [activePanel]);

  const panels: { id: Panel; label: string; icon: React.ReactNode }[] = [
    { id: "top-concepts", label: "Top Concepts", icon: <Crown size={14} /> },
    { id: "galaxies", label: "Galaxy Watch", icon: <Orbit size={14} /> },
    { id: "reflection-impact", label: "Reflection Impact", icon: <PenLine size={14} /> },
    { id: "domain-balance", label: "Domain Balance", icon: <BarChart3 size={14} /> },
    { id: "emerging-signals", label: "Emerging Signals", icon: <Zap size={14} /> },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Panel selector */}
      <div className="border-b border-zinc-800 px-4 py-2 flex items-center gap-2 shrink-0 overflow-x-auto">
        {panels.map((p) => (
          <button
            key={p.id}
            onClick={() => setActivePanel(p.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs whitespace-nowrap transition-colors ${
              activePanel === p.id
                ? "bg-zinc-700 text-zinc-100"
                : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"
            }`}
          >
            {p.icon}
            {p.label}
          </button>
        ))}
        <button
          onClick={() => loadPanel(activePanel)}
          className="ml-auto text-zinc-500 hover:text-zinc-300 p-1.5 rounded hover:bg-zinc-800"
          title="Refresh"
        >
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading && (
          <div className="flex items-center justify-center h-32">
            <Loader2 size={20} className="animate-spin text-zinc-500" />
            <span className="ml-2 text-sm text-zinc-500">Loading observatory data...</span>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-3 rounded bg-red-900/20 border border-red-800 text-red-400 text-sm">
            <AlertTriangle size={16} />
            {error}
          </div>
        )}

        {!loading && !error && activePanel === "top-concepts" && topConcepts && (
          <TopConceptsView data={topConcepts} />
        )}
        {!loading && !error && activePanel === "galaxies" && galaxyWatch && (
          <GalaxyWatchView data={galaxyWatch} />
        )}
        {!loading && !error && activePanel === "reflection-impact" && reflectionImpact && (
          <ReflectionImpactView data={reflectionImpact} />
        )}
        {!loading && !error && activePanel === "domain-balance" && domainBalance && (
          <DomainBalanceView data={domainBalance} />
        )}
        {!loading && !error && activePanel === "emerging-signals" && emergingSignals && (
          <EmergingSignalsView data={emergingSignals} />
        )}
      </div>
    </div>
  );
}

/* ---- Top Concepts ---- */
function TopConceptsView({ data }: { data: TopConceptsResult }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-zinc-300">
          Top Concepts by Meaning Mass
        </h3>
        <span className="text-xs text-zinc-500">{data.total_fragments} total fragments</span>
      </div>

      {data.concepts.length === 0 ? (
        <p className="text-sm text-zinc-500">No fragments yet. Add fragments to see top concepts.</p>
      ) : (
        <div className="space-y-2">
          {data.concepts.map((c, i) => (
            <div
              key={c.fragment_id}
              className="bg-zinc-900 border border-zinc-800 rounded-lg p-3"
            >
              <div className="flex items-start gap-3">
                <span className="text-xs text-zinc-600 font-mono w-6 shrink-0 pt-0.5">
                  #{i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-zinc-200 leading-relaxed">{c.text}</p>
                  <div className="flex items-center gap-2 mt-2 flex-wrap">
                    {c.domain && (
                      <span
                        className="text-xs px-1.5 py-0.5 rounded"
                        style={{
                          backgroundColor: `${DOMAIN_COLORS[c.domain] || "#71717a"}20`,
                          color: DOMAIN_COLORS[c.domain] || "#71717a",
                        }}
                      >
                        {c.domain}
                      </span>
                    )}
                    <span className="text-xs text-amber-400 font-mono">
                      mass: {c.meaning_mass.toFixed(3)}
                    </span>
                    <span className="text-xs text-zinc-500">
                      {c.edge_count} edges
                    </span>
                    {c.is_gravity_hub && (
                      <span className="text-xs text-cyan-400 flex items-center gap-0.5">
                        <Star size={10} /> hub
                      </span>
                    )}
                    {c.is_galaxy_center && (
                      <span className="text-xs text-amber-300 flex items-center gap-0.5">
                        <Crown size={10} /> center
                      </span>
                    )}
                    {c.mass_trend !== 0 && (
                      <span
                        className={`text-xs flex items-center gap-0.5 ${
                          c.mass_trend > 0 ? "text-green-400" : "text-red-400"
                        }`}
                      >
                        {c.mass_trend > 0 ? (
                          <TrendingUp size={10} />
                        ) : (
                          <TrendingDown size={10} />
                        )}
                        {c.mass_trend > 0 ? "+" : ""}
                        {c.mass_trend.toFixed(3)}
                      </span>
                    )}
                  </div>
                </div>
                {/* Mass bar */}
                <div className="w-20 shrink-0">
                  <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-amber-500 rounded-full"
                      style={{
                        width: `${Math.min(100, c.meaning_mass * 100)}%`,
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---- Galaxy Watch ---- */
function GalaxyWatchView({ data }: { data: GalaxyWatchResult }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-zinc-300">Galaxy Watch</h3>
        <span className="text-xs text-zinc-500">{data.total_galaxies} galaxies detected</span>
      </div>

      {data.galaxies.length === 0 ? (
        <p className="text-sm text-zinc-500">
          No galaxies detected. Add more fragments and generate edges to form galaxies.
        </p>
      ) : (
        <div className="grid gap-3">
          {data.galaxies.map((g) => (
            <div
              key={g.cluster_id}
              className="bg-zinc-900 border border-zinc-800 rounded-lg p-4"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Orbit size={16} className="text-purple-400" />
                  <span className="text-sm font-medium text-zinc-200">
                    Galaxy #{g.cluster_id}
                  </span>
                  {g.growth !== 0 && (
                    <span
                      className={`text-xs flex items-center gap-0.5 ${
                        g.growth > 0 ? "text-green-400" : "text-red-400"
                      }`}
                    >
                      {g.growth > 0 ? (
                        <TrendingUp size={10} />
                      ) : (
                        <TrendingDown size={10} />
                      )}
                      {g.growth > 0 ? "+" : ""}
                      {g.growth}
                    </span>
                  )}
                </div>
                <span className="text-xs text-zinc-500">{g.size} fragments</span>
              </div>

              {/* Stats grid */}
              <div className="grid grid-cols-3 gap-3 mb-3">
                <div className="text-center">
                  <div className="text-xs text-zinc-500">Density</div>
                  <div className="text-sm font-mono text-zinc-300">
                    {g.density.toFixed(3)}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-xs text-zinc-500">Entropy</div>
                  <div className="text-sm font-mono text-zinc-300">
                    {g.domain_entropy.toFixed(3)}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-xs text-zinc-500">Domains</div>
                  <div className="text-sm font-mono text-zinc-300">
                    {g.member_domains.length}
                  </div>
                </div>
              </div>

              {/* Center fragment */}
              <div className="bg-zinc-800/50 rounded p-2 mb-2">
                <div className="flex items-center gap-1 text-xs text-amber-400 mb-1">
                  <Crown size={10} />
                  Center Fragment
                </div>
                <p className="text-xs text-zinc-300 leading-relaxed">
                  {g.center_fragment_text}
                </p>
              </div>

              {/* Member domains */}
              {g.member_domains.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {g.member_domains.map((d) => (
                    <span
                      key={d}
                      className="text-xs px-1.5 py-0.5 rounded"
                      style={{
                        backgroundColor: `${DOMAIN_COLORS[d] || "#71717a"}20`,
                        color: DOMAIN_COLORS[d] || "#71717a",
                      }}
                    >
                      {d}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---- Reflection Impact ---- */
function ReflectionImpactView({ data }: { data: ReflectionImpactResult }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-zinc-300">Reflection Impact</h3>
        <div className="flex items-center gap-3 text-xs text-zinc-500">
          <span>avg edges: {data.avg_edges_created.toFixed(1)}</span>
          <span>avg mass boost: {data.avg_mass_boost.toFixed(3)}</span>
        </div>
      </div>

      {data.reflections.length === 0 ? (
        <p className="text-sm text-zinc-500">
          No reflections yet. Write reflections to see their structural impact.
        </p>
      ) : (
        <div className="space-y-2">
          {data.reflections.map((r) => (
            <div
              key={r.reflection_id}
              className="bg-zinc-900 border border-zinc-800 rounded-lg p-3"
            >
              <p className="text-sm text-zinc-200 leading-relaxed mb-2">
                {r.reflection_text}
              </p>
              <div className="grid grid-cols-4 gap-2">
                <div className="bg-zinc-800/50 rounded p-2 text-center">
                  <div className="text-xs text-zinc-500">Linked</div>
                  <div className="text-sm font-mono text-blue-400">
                    {r.linked_fragment_count}
                  </div>
                </div>
                <div className="bg-zinc-800/50 rounded p-2 text-center">
                  <div className="text-xs text-zinc-500">Edges</div>
                  <div className="text-sm font-mono text-green-400">
                    {r.edges_created}
                  </div>
                </div>
                <div className="bg-zinc-800/50 rounded p-2 text-center">
                  <div className="text-xs text-zinc-500">Mass Boost</div>
                  <div className="text-sm font-mono text-amber-400">
                    {r.mass_boost.toFixed(3)}
                  </div>
                </div>
                <div className="bg-zinc-800/50 rounded p-2 text-center">
                  <div className="text-xs text-zinc-500">Clusters</div>
                  <div className="text-sm font-mono text-purple-400">
                    {r.clusters_touched}
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between mt-2 text-xs text-zinc-500">
                <span>{new Date(r.timestamp).toLocaleDateString()}</span>
                {r.galaxies_touched > 0 && (
                  <span className="text-purple-400">
                    touches {r.galaxies_touched} galaxies
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---- Domain Balance ---- */
function DomainBalanceView({ data }: { data: DomainBalanceResult }) {
  const maxCount = Math.max(...data.domains.map((d) => d.fragment_count), 1);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-zinc-300">Domain Balance</h3>
        <span className="text-xs text-zinc-500">{data.total_fragments} total fragments</span>
      </div>

      {/* Warnings */}
      {data.dominant.length > 0 && (
        <div className="flex items-center gap-2 p-2 rounded bg-amber-900/20 border border-amber-800 text-amber-400 text-xs">
          <AlertTriangle size={14} />
          Dominant domains: {data.dominant.join(", ")}
        </div>
      )}
      {data.underrepresented.length > 0 && (
        <div className="flex items-center gap-2 p-2 rounded bg-blue-900/20 border border-blue-800 text-blue-400 text-xs">
          <Minus size={14} />
          Underrepresented: {data.underrepresented.join(", ")}
        </div>
      )}

      {data.domains.length === 0 ? (
        <p className="text-sm text-zinc-500">No fragments yet.</p>
      ) : (
        <div className="space-y-2 mt-3">
          {data.domains.map((d) => (
            <div
              key={d.domain}
              className="bg-zinc-900 border border-zinc-800 rounded-lg p-3"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{
                      backgroundColor: DOMAIN_COLORS[d.domain] || "#71717a",
                    }}
                  />
                  <span className="text-sm text-zinc-200">{d.domain}</span>
                </div>
                <span className="text-xs text-zinc-500">
                  {d.fragment_count} ({d.percentage}%)
                </span>
              </div>
              {/* Bar */}
              <div className="h-2 bg-zinc-800 rounded-full overflow-hidden mb-2">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${(d.fragment_count / maxCount) * 100}%`,
                    backgroundColor: DOMAIN_COLORS[d.domain] || "#71717a",
                  }}
                />
              </div>
              <div className="flex items-center gap-3 text-xs text-zinc-500">
                <span>{d.edge_count} edges</span>
                <span>avg mass: {d.avg_meaning_mass.toFixed(3)}</span>
                {d.hub_count > 0 && (
                  <span className="text-cyan-400">{d.hub_count} hubs</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---- Emerging Signals ---- */
function EmergingSignalsView({ data }: { data: EmergingSignalsResult }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-zinc-300">Emerging Signals</h3>
        <span className="text-xs text-zinc-500">{data.total_signals} signals detected</span>
      </div>

      {data.signals.length === 0 ? (
        <p className="text-sm text-zinc-500">
          No emerging signals detected. Add more fragments over time to detect rising concepts.
        </p>
      ) : (
        <div className="space-y-2">
          {data.signals.map((s) => (
            <div
              key={s.fragment_id}
              className="bg-zinc-900 border border-zinc-800 rounded-lg p-3"
            >
              <div className="flex items-start gap-3">
                <div className="shrink-0 pt-0.5">
                  <Zap
                    size={14}
                    className={
                      s.signal_strength > 0.3
                        ? "text-yellow-400"
                        : s.signal_strength > 0.1
                        ? "text-amber-400"
                        : "text-zinc-500"
                    }
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-zinc-200 leading-relaxed">{s.text}</p>
                  <div className="flex items-center gap-2 mt-2 flex-wrap">
                    {s.domain && (
                      <span
                        className="text-xs px-1.5 py-0.5 rounded"
                        style={{
                          backgroundColor: `${DOMAIN_COLORS[s.domain] || "#71717a"}20`,
                          color: DOMAIN_COLORS[s.domain] || "#71717a",
                        }}
                      >
                        {s.domain}
                      </span>
                    )}
                    <span className="text-xs text-amber-400 font-mono">
                      mass: {s.current_mass.toFixed(3)}
                    </span>
                    {s.mass_change !== 0 && (
                      <span
                        className={`text-xs font-mono ${
                          s.mass_change > 0 ? "text-green-400" : "text-red-400"
                        }`}
                      >
                        {s.mass_change > 0 ? "+" : ""}
                        {s.mass_change.toFixed(3)}
                      </span>
                    )}
                    <span className="text-xs font-mono text-yellow-400">
                      signal: {s.signal_strength.toFixed(3)}
                    </span>
                    {s.is_domain_crossing && (
                      <span className="text-xs text-purple-400 bg-purple-900/20 px-1.5 py-0.5 rounded">
                        cross-domain
                      </span>
                    )}
                    {s.is_reflection_linked && (
                      <span className="text-xs text-blue-400 bg-blue-900/20 px-1.5 py-0.5 rounded">
                        reflection-linked
                      </span>
                    )}
                  </div>
                </div>
                {/* Signal strength bar */}
                <div className="w-16 shrink-0">
                  <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-yellow-500 rounded-full"
                      style={{
                        width: `${Math.min(100, s.signal_strength * 200)}%`,
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
