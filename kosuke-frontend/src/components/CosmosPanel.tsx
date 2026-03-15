import { useState, useEffect } from "react";
import { api, type CosmosData } from "@/lib/api";
import { Globe, Users, Link2, Orbit, Star, Loader2 } from "lucide-react";

type CosmosView = "overview" | "authors" | "cross-edges" | "shared-galaxies" | "collective-hubs";
type CosmosMode = "personal" | "shared" | "global";

const AUTHOR_COLORS = [
  "#60a5fa", "#f472b6", "#34d399", "#fbbf24", "#a78bfa",
  "#fb923c", "#22d3ee", "#e879f9", "#4ade80", "#f87171",
];

function getAuthorColor(author: string, allAuthors: string[]): string {
  const idx = allAuthors.indexOf(author);
  return AUTHOR_COLORS[idx % AUTHOR_COLORS.length];
}

export function CosmosPanel() {
  const [data, setData] = useState<CosmosData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [view, setView] = useState<CosmosView>("overview");
  const [cosmosMode, setCosmosMode] = useState<CosmosMode>("global");
  const [selectedAuthor, setSelectedAuthor] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError("");
    try {
      const result = await api.getCosmosData();
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load cosmos data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const allAuthorNames = data?.authors.map((a) => a.name) ?? [];

  // Filter data based on cosmos mode
  const filteredCrossEdges = data?.cross_cosmos_edges.filter((e) => {
    if (cosmosMode === "personal" && selectedAuthor) {
      return e.fragment_a_author === selectedAuthor || e.fragment_b_author === selectedAuthor;
    }
    if (cosmosMode === "shared") {
      return true; // cross-edges are inherently shared
    }
    return true; // global
  }) ?? [];

  const filteredGalaxies = data?.shared_galaxies.filter((g) => {
    if (cosmosMode === "personal" && selectedAuthor) {
      return g.authors.includes(selectedAuthor);
    }
    return true;
  }) ?? [];

  const filteredHubs = data?.collective_hubs.filter((h) => {
    if (cosmosMode === "personal" && selectedAuthor) {
      return (h.author || "anonymous") === selectedAuthor;
    }
    if (cosmosMode === "shared") {
      return h.cross_author_edges > 0;
    }
    return true;
  }) ?? [];

  const views: { id: CosmosView; label: string; icon: React.ReactNode }[] = [
    { id: "overview", label: "Overview", icon: <Globe size={14} /> },
    { id: "authors", label: "Authors", icon: <Users size={14} /> },
    { id: "cross-edges", label: "Cross-Cosmos", icon: <Link2 size={14} /> },
    { id: "shared-galaxies", label: "Shared Galaxies", icon: <Orbit size={14} /> },
    { id: "collective-hubs", label: "Collective Hubs", icon: <Star size={14} /> },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Cosmos Mode Selector */}
      <div className="border-b border-zinc-800 px-4 py-3 flex items-center gap-3">
        <span className="text-xs text-zinc-500 mr-1">Cosmos:</span>
        {(["personal", "shared", "global"] as CosmosMode[]).map((mode) => (
          <button
            key={mode}
            onClick={() => {
              setCosmosMode(mode);
              if (mode !== "personal") setSelectedAuthor(null);
            }}
            className={`px-3 py-1.5 text-xs rounded-md transition-colors capitalize ${
              cosmosMode === mode
                ? "bg-violet-500/20 text-violet-300 border border-violet-500/30"
                : "text-zinc-500 hover:text-zinc-300 border border-transparent"
            }`}
          >
            {mode}
          </button>
        ))}

        {cosmosMode === "personal" && data && (
          <select
            value={selectedAuthor ?? ""}
            onChange={(e) => setSelectedAuthor(e.target.value || null)}
            className="ml-2 bg-zinc-900 border border-zinc-700 rounded-md px-2 py-1 text-xs text-zinc-300 focus:outline-none focus:border-violet-500"
          >
            <option value="">Select author...</option>
            {data.authors.map((a) => (
              <option key={a.name} value={a.name}>
                {a.name} ({a.fragment_count} fragments)
              </option>
            ))}
          </select>
        )}

        <button
          onClick={loadData}
          disabled={loading}
          className="ml-auto px-3 py-1.5 text-xs rounded-md bg-zinc-800 text-zinc-300 hover:bg-zinc-700 disabled:opacity-50 transition-colors"
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : "Refresh"}
        </button>
      </div>

      {/* Sub-navigation */}
      <div className="border-b border-zinc-800 px-4 flex gap-1">
        {views.map((v) => (
          <button
            key={v.id}
            onClick={() => setView(v.id)}
            className={`flex items-center gap-1.5 px-3 py-2.5 text-xs border-b-2 transition-colors ${
              view === v.id
                ? "border-violet-400 text-violet-300"
                : "border-transparent text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {v.icon}
            {v.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {error && <p className="text-red-400 text-xs mb-3">{error}</p>}

        {loading && !data && (
          <div className="flex items-center justify-center py-12">
            <Loader2 size={24} className="animate-spin text-violet-400" />
          </div>
        )}

        {data && view === "overview" && (
          <OverviewView data={data} allAuthors={allAuthorNames} />
        )}
        {data && view === "authors" && (
          <AuthorsView
            data={data}
            allAuthors={allAuthorNames}
            onSelectAuthor={(a) => {
              setSelectedAuthor(a);
              setCosmosMode("personal");
            }}
          />
        )}
        {data && view === "cross-edges" && (
          <CrossEdgesView edges={filteredCrossEdges} allAuthors={allAuthorNames} />
        )}
        {data && view === "shared-galaxies" && (
          <SharedGalaxiesView galaxies={filteredGalaxies} allAuthors={allAuthorNames} />
        )}
        {data && view === "collective-hubs" && (
          <CollectiveHubsView hubs={filteredHubs} allAuthors={allAuthorNames} />
        )}
      </div>
    </div>
  );
}

function OverviewView({ data, allAuthors }: { data: CosmosData; allAuthors: string[] }) {
  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-3">
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-violet-400">{data.total_authors}</p>
          <p className="text-xs text-zinc-500 mt-1">Authors</p>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-blue-400">{data.total_fragments}</p>
          <p className="text-xs text-zinc-500 mt-1">Fragments</p>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-amber-400">{data.total_cross_edges}</p>
          <p className="text-xs text-zinc-500 mt-1">Cross-Cosmos Edges</p>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-emerald-400">{data.total_shared_galaxies}</p>
          <p className="text-xs text-zinc-500 mt-1">Shared Galaxies</p>
        </div>
      </div>

      {/* Author distribution */}
      {data.authors.length > 0 && (
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <h3 className="text-sm font-medium text-zinc-300 mb-3">Author Distribution</h3>
          <div className="space-y-2">
            {data.authors.map((a) => {
              const pct = data.total_fragments > 0
                ? Math.round((a.fragment_count / data.total_fragments) * 100)
                : 0;
              const color = getAuthorColor(a.name, allAuthors);
              return (
                <div key={a.name} className="flex items-center gap-3">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: color }}
                  />
                  <span className="text-xs text-zinc-300 w-24 truncate">{a.name}</span>
                  <div className="flex-1 h-2 bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${pct}%`, backgroundColor: color }}
                    />
                  </div>
                  <span className="text-xs text-zinc-500 w-16 text-right">
                    {a.fragment_count} ({pct}%)
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Top cross-edges preview */}
      {data.cross_cosmos_edges.length > 0 && (
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <h3 className="text-sm font-medium text-zinc-300 mb-3">
            Top Cross-Cosmos Connections
          </h3>
          <div className="space-y-2">
            {data.cross_cosmos_edges.slice(0, 3).map((e, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                <span
                  className="px-1.5 py-0.5 rounded"
                  style={{
                    backgroundColor: getAuthorColor(e.fragment_a_author, allAuthors) + "20",
                    color: getAuthorColor(e.fragment_a_author, allAuthors),
                  }}
                >
                  {e.fragment_a_author}
                </span>
                <span className="text-zinc-600">↔</span>
                <span
                  className="px-1.5 py-0.5 rounded"
                  style={{
                    backgroundColor: getAuthorColor(e.fragment_b_author, allAuthors) + "20",
                    color: getAuthorColor(e.fragment_b_author, allAuthors),
                  }}
                >
                  {e.fragment_b_author}
                </span>
                <span className="text-zinc-500 ml-auto">
                  similarity: {(e.similarity * 100).toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function AuthorsView({
  data,
  allAuthors,
  onSelectAuthor,
}: {
  data: CosmosData;
  allAuthors: string[];
  onSelectAuthor: (author: string) => void;
}) {
  return (
    <div className="space-y-3">
      {data.authors.length === 0 ? (
        <p className="text-zinc-600 text-sm text-center py-8">
          No authors found. Add fragments with an author field to populate the cosmos.
        </p>
      ) : (
        data.authors.map((a) => {
          const color = getAuthorColor(a.name, allAuthors);
          return (
            <div
              key={a.name}
              onClick={() => onSelectAuthor(a.name)}
              className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4 hover:border-zinc-700 transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-3 mb-3">
                <span
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: color }}
                />
                <span className="text-sm font-medium text-zinc-200">{a.name}</span>
              </div>
              <div className="grid grid-cols-5 gap-3 text-center">
                <div>
                  <p className="text-lg font-bold text-zinc-200">{a.fragment_count}</p>
                  <p className="text-xs text-zinc-500">Fragments</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-zinc-200">{a.edge_count}</p>
                  <p className="text-xs text-zinc-500">Edges</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-zinc-200">{a.gravity_hub_count}</p>
                  <p className="text-xs text-zinc-500">Hubs</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-zinc-200">{a.galaxy_count}</p>
                  <p className="text-xs text-zinc-500">Galaxies</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-zinc-200">
                    {a.avg_meaning_mass.toFixed(3)}
                  </p>
                  <p className="text-xs text-zinc-500">Avg Mass</p>
                </div>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}

function CrossEdgesView({
  edges,
  allAuthors,
}: {
  edges: CosmosData["cross_cosmos_edges"];
  allAuthors: string[];
}) {
  return (
    <div className="space-y-3">
      {edges.length === 0 ? (
        <p className="text-zinc-600 text-sm text-center py-8">
          No cross-cosmos edges found. Add fragments from multiple authors and generate edges.
        </p>
      ) : (
        <>
          <p className="text-xs text-zinc-500 mb-2">
            {edges.length} cross-cosmos connection{edges.length !== 1 ? "s" : ""}
          </p>
          {edges.map((e, i) => (
            <div
              key={i}
              className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 space-y-2"
            >
              <div className="flex items-start gap-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className="text-xs px-1.5 py-0.5 rounded"
                      style={{
                        backgroundColor: getAuthorColor(e.fragment_a_author, allAuthors) + "20",
                        color: getAuthorColor(e.fragment_a_author, allAuthors),
                      }}
                    >
                      {e.fragment_a_author}
                    </span>
                  </div>
                  <p className="text-xs text-zinc-300">{e.fragment_a_text}</p>
                </div>
                <div className="flex flex-col items-center px-2 shrink-0">
                  <span className="text-xs text-amber-400 font-mono">
                    {(e.similarity * 100).toFixed(1)}%
                  </span>
                  <span className="text-zinc-600 text-xs">↔</span>
                  <span className="text-xs text-zinc-600">{e.relation_type}</span>
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className="text-xs px-1.5 py-0.5 rounded"
                      style={{
                        backgroundColor: getAuthorColor(e.fragment_b_author, allAuthors) + "20",
                        color: getAuthorColor(e.fragment_b_author, allAuthors),
                      }}
                    >
                      {e.fragment_b_author}
                    </span>
                  </div>
                  <p className="text-xs text-zinc-300">{e.fragment_b_text}</p>
                </div>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

function SharedGalaxiesView({
  galaxies,
  allAuthors,
}: {
  galaxies: CosmosData["shared_galaxies"];
  allAuthors: string[];
}) {
  return (
    <div className="space-y-3">
      {galaxies.length === 0 ? (
        <p className="text-zinc-600 text-sm text-center py-8">
          No shared galaxies detected. Shared galaxies form when clusters contain fragments from multiple authors.
        </p>
      ) : (
        galaxies.map((g) => (
          <div
            key={g.cluster_id}
            className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Orbit size={14} className="text-violet-400" />
                <span className="text-sm font-medium text-zinc-200">
                  Galaxy #{g.cluster_id}
                </span>
              </div>
              <span className="text-xs text-zinc-500">
                {g.size} fragments · density {g.density.toFixed(3)}
              </span>
            </div>

            {/* Author composition */}
            <div className="flex flex-wrap gap-2 mb-3">
              {g.authors.map((a) => {
                const count = g.author_counts[a] ?? 0;
                const color = getAuthorColor(a, allAuthors);
                return (
                  <span
                    key={a}
                    className="text-xs px-2 py-1 rounded-md flex items-center gap-1"
                    style={{
                      backgroundColor: color + "15",
                      color: color,
                      border: `1px solid ${color}30`,
                    }}
                  >
                    <span
                      className="w-1.5 h-1.5 rounded-full"
                      style={{ backgroundColor: color }}
                    />
                    {a}: {count}
                  </span>
                );
              })}
            </div>

            {/* Center fragment */}
            <div className="bg-zinc-800/50 rounded-md p-2">
              <div className="flex items-center gap-1.5 mb-1">
                <Star size={10} className="text-amber-400" />
                <span className="text-xs text-zinc-500">Center</span>
                {g.center_author && (
                  <span
                    className="text-xs px-1 py-0.5 rounded"
                    style={{
                      backgroundColor: getAuthorColor(g.center_author, allAuthors) + "20",
                      color: getAuthorColor(g.center_author, allAuthors),
                    }}
                  >
                    {g.center_author}
                  </span>
                )}
              </div>
              <p className="text-xs text-zinc-300">{g.center_fragment_text}</p>
            </div>

            <div className="mt-2 text-xs text-zinc-500">
              Domain entropy: {g.domain_entropy.toFixed(3)}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

function CollectiveHubsView({
  hubs,
  allAuthors,
}: {
  hubs: CosmosData["collective_hubs"];
  allAuthors: string[];
}) {
  const maxMass = Math.max(...hubs.map((h) => h.meaning_mass), 0.001);

  return (
    <div className="space-y-3">
      {hubs.length === 0 ? (
        <p className="text-zinc-600 text-sm text-center py-8">
          No collective hubs found. Generate gravity edges and detect galaxies to identify hubs.
        </p>
      ) : (
        <>
          <p className="text-xs text-zinc-500 mb-2">
            {hubs.length} collective gravity hub{hubs.length !== 1 ? "s" : ""}
          </p>
          {hubs.map((h) => {
            const author = h.author || "anonymous";
            const color = getAuthorColor(author, allAuthors);
            const massPct = maxMass > 0 ? (h.meaning_mass / maxMass) * 100 : 0;

            return (
              <div
                key={h.fragment_id}
                className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span
                      className="text-xs px-1.5 py-0.5 rounded"
                      style={{
                        backgroundColor: color + "20",
                        color: color,
                      }}
                    >
                      {author}
                    </span>
                    {h.domain && (
                      <span className="text-xs text-emerald-400/70 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                        {h.domain}
                      </span>
                    )}
                  </div>
                  {h.cross_author_edges > 0 && (
                    <span className="text-xs text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">
                      {h.cross_author_edges} cross-author
                    </span>
                  )}
                </div>

                <p className="text-xs text-zinc-300 mb-2">{h.text}</p>

                <div className="flex items-center gap-3">
                  <div className="flex-1">
                    <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-cyan-400 transition-all"
                        style={{ width: `${massPct}%` }}
                      />
                    </div>
                  </div>
                  <span className="text-xs text-cyan-400 font-mono shrink-0">
                    mass: {h.meaning_mass.toFixed(3)}
                  </span>
                  <span className="text-xs text-zinc-500 shrink-0">
                    {h.edge_count} edges
                  </span>
                </div>
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}
