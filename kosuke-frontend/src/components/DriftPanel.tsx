import { useState, useCallback, useMemo } from "react";
import {
  api,
  type DriftAnalysis,
  type TimeSliceMetrics,
  type DriftVector,
} from "@/lib/api";
import { Clock, TrendingUp, TrendingDown, Minus, Sparkles, RefreshCw } from "lucide-react";

// Domain colors (shared with NetworkPanel)
const DOMAIN_COLORS: Record<string, string> = {
  technology: "#3b82f6",
  philosophy: "#a855f7",
  body: "#f97316",
  urban: "#14b8a6",
  culture: "#ec4899",
  art: "#10b981",
  science: "#06b6d4",
  nature: "#22c55e",
  politics: "#ef4444",
  economics: "#eab308",
  psychology: "#8b5cf6",
  literature: "#d946ef",
  music: "#f59e0b",
  spirituality: "#6366f1",
  mathematics: "#0ea5e9",
};

const DRIFT_COLORS: Record<string, string> = {
  emergence: "#22c55e",
  migration: "#3b82f6",
  collapse: "#ef4444",
  stable: "#71717a",
};

const DRIFT_ICONS: Record<string, React.ReactNode> = {
  emergence: <TrendingUp size={14} className="text-green-400" />,
  migration: <Minus size={14} className="text-blue-400" />,
  collapse: <TrendingDown size={14} className="text-red-400" />,
  stable: <Minus size={14} className="text-zinc-500" />,
};

export function DriftPanel() {
  const [driftData, setDriftData] = useState<DriftAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<"monthly" | "quarterly" | "yearly">("monthly");
  const [selectedSliceIndex, setSelectedSliceIndex] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  const analyzeDrift = useCallback(async (sliceMode: "monthly" | "quarterly" | "yearly") => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.analyzeDrift(sliceMode);
      setDriftData(data);
      // Select the last slice by default
      if (data.slices.length > 0) {
        setSelectedSliceIndex(data.slices.length - 1);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to analyze drift");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleModeChange = (newMode: "monthly" | "quarterly" | "yearly") => {
    setMode(newMode);
    analyzeDrift(newMode);
  };

  const selectedSlice: TimeSliceMetrics | null = useMemo(() => {
    if (!driftData || driftData.slices.length === 0) return null;
    return driftData.slices[selectedSliceIndex] || null;
  }, [driftData, selectedSliceIndex]);

  // Get drift vectors relevant to the selected slice transition
  const relevantDrifts: DriftVector[] = useMemo(() => {
    if (!driftData || selectedSliceIndex === 0) return [];
    return driftData.drift_vectors;
  }, [driftData, selectedSliceIndex]);

  // Sort drifts by absolute mass delta
  const sortedDrifts = useMemo(() => {
    return [...relevantDrifts].sort(
      (a, b) => Math.abs(b.mass_delta) - Math.abs(a.mass_delta)
    );
  }, [relevantDrifts]);

  // Max mass for bar scaling
  const maxMass = useMemo(() => {
    if (!selectedSlice) return 1;
    const masses = Object.values(selectedSlice.meaning_mass_map);
    return Math.max(...masses, 0.1);
  }, [selectedSlice]);

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="border-b border-zinc-800 px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => analyzeDrift(mode)}
            disabled={loading}
            className="flex items-center gap-1.5 text-xs bg-zinc-800 hover:bg-zinc-700 text-purple-400 px-2.5 py-1.5 rounded transition-colors disabled:opacity-50"
          >
            <Clock size={14} className={loading ? "animate-spin" : ""} />
            {loading ? "Analyzing..." : "Analyze Drift"}
          </button>

          {/* Mode selector */}
          <div className="flex items-center gap-1 bg-zinc-900 rounded-lg p-0.5">
            {(["monthly", "quarterly", "yearly"] as const).map((m) => (
              <button
                key={m}
                onClick={() => handleModeChange(m)}
                className={`text-xs px-2.5 py-1 rounded transition-colors ${
                  mode === m
                    ? "bg-zinc-700 text-zinc-200"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                {m.charAt(0).toUpperCase() + m.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Drift summary stats */}
        {driftData && (
          <div className="flex items-center gap-4 text-xs">
            <span className="text-green-400 flex items-center gap-1">
              <TrendingUp size={12} />
              {driftData.emergence_count} emerge
            </span>
            <span className="text-blue-400 flex items-center gap-1">
              <RefreshCw size={12} />
              {driftData.migration_count} migrate
            </span>
            <span className="text-red-400 flex items-center gap-1">
              <TrendingDown size={12} />
              {driftData.collapse_count} collapse
            </span>
            <span className="text-zinc-500 flex items-center gap-1">
              <Minus size={12} />
              {driftData.stable_count} stable
            </span>
          </div>
        )}
      </div>

      {error && (
        <div className="px-4 py-2 bg-red-500/10 border-b border-red-500/20 text-red-400 text-xs">
          {error}
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 overflow-hidden flex">
        {!driftData ? (
          <div className="flex flex-col items-center justify-center flex-1 text-center text-zinc-600 py-12">
            <Clock size={32} className="mb-3 text-zinc-700" />
            <p className="text-sm">No drift data yet</p>
            <p className="text-xs mt-1">
              Click &quot;Analyze Drift&quot; to track how meaning evolves over time
            </p>
          </div>
        ) : (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Timeline slider */}
            {driftData.slices.length > 0 && (
              <div className="border-b border-zinc-800 px-4 py-3 shrink-0">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-xs text-zinc-500">Timeline</span>
                  <span className="text-xs text-zinc-400 font-mono">
                    {selectedSlice?.slice_label || "—"}
                  </span>
                </div>

                {/* Slider track */}
                <div className="relative">
                  <input
                    type="range"
                    min={0}
                    max={driftData.slices.length - 1}
                    value={selectedSliceIndex}
                    onChange={(e) => setSelectedSliceIndex(Number(e.target.value))}
                    className="w-full h-1 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-purple-500"
                  />
                  {/* Slice labels */}
                  <div className="flex justify-between mt-1">
                    {driftData.slices.map((s, i) => (
                      <button
                        key={i}
                        onClick={() => setSelectedSliceIndex(i)}
                        className={`text-[10px] transition-colors ${
                          i === selectedSliceIndex
                            ? "text-purple-400 font-medium"
                            : "text-zinc-600 hover:text-zinc-400"
                        }`}
                      >
                        {s.slice_label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Content grid */}
            <div className="flex-1 overflow-auto">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 h-full">
                {/* Left: Slice metrics + Galaxy evolution */}
                <div className="border-r border-zinc-800 overflow-auto">
                  {/* Selected slice metrics */}
                  {selectedSlice && (
                    <div className="p-4 border-b border-zinc-800">
                      <h3 className="text-sm font-medium text-zinc-200 mb-3 flex items-center gap-2">
                        <Clock size={14} className="text-purple-400" />
                        Slice: {selectedSlice.slice_label}
                      </h3>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
                          <div className="text-lg font-semibold text-zinc-100">
                            {selectedSlice.fragment_count}
                          </div>
                          <div className="text-xs text-zinc-500">fragments</div>
                        </div>
                        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
                          <div className="text-lg font-semibold text-zinc-100">
                            {selectedSlice.edge_count}
                          </div>
                          <div className="text-xs text-zinc-500">edges</div>
                        </div>
                        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
                          <div className="text-lg font-semibold text-amber-400">
                            {selectedSlice.galaxy_count}
                          </div>
                          <div className="text-xs text-zinc-500">galaxies</div>
                        </div>
                        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
                          <div className="text-lg font-semibold text-cyan-400">
                            {selectedSlice.gravity_hub_count}
                          </div>
                          <div className="text-xs text-zinc-500">gravity hubs</div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Galaxy evolution chart */}
                  <div className="p-4">
                    <h3 className="text-sm font-medium text-zinc-200 mb-3 flex items-center gap-2">
                      <Sparkles size={14} className="text-amber-400" />
                      Galaxy Evolution
                    </h3>
                    <div className="space-y-1">
                      {driftData.slices.map((s, i) => (
                        <div
                          key={i}
                          onClick={() => setSelectedSliceIndex(i)}
                          className={`flex items-center gap-3 p-2 rounded cursor-pointer transition-colors ${
                            i === selectedSliceIndex
                              ? "bg-zinc-800 border border-zinc-700"
                              : "hover:bg-zinc-900"
                          }`}
                        >
                          <span className="text-xs text-zinc-500 w-16 shrink-0 font-mono">
                            {s.slice_label}
                          </span>
                          <div className="flex-1 flex items-center gap-2">
                            {/* Galaxy bar */}
                            <div className="flex-1 h-4 bg-zinc-900 rounded overflow-hidden flex">
                              <div
                                className="h-full bg-amber-500/30 transition-all"
                                style={{
                                  width: `${Math.min(100, (s.galaxy_count / Math.max(1, ...driftData.slices.map(sl => sl.galaxy_count))) * 100)}%`,
                                }}
                              />
                            </div>
                            <span className="text-xs text-amber-400 w-6 text-right">
                              {s.galaxy_count}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            {/* Hub count */}
                            <div className="flex-1 h-4 bg-zinc-900 rounded overflow-hidden flex w-16">
                              <div
                                className="h-full bg-cyan-500/30 transition-all"
                                style={{
                                  width: `${Math.min(100, (s.gravity_hub_count / Math.max(1, ...driftData.slices.map(sl => sl.gravity_hub_count))) * 100)}%`,
                                }}
                              />
                            </div>
                            <span className="text-xs text-cyan-400 w-6 text-right">
                              {s.gravity_hub_count}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="flex items-center gap-4 mt-3 text-[10px] text-zinc-600">
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-2 bg-amber-500/30 rounded" />
                        galaxies
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-2 bg-cyan-500/30 rounded" />
                        gravity hubs
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right: Drift vectors */}
                <div className="overflow-auto">
                  <div className="p-4">
                    <h3 className="text-sm font-medium text-zinc-200 mb-3 flex items-center gap-2">
                      <TrendingUp size={14} className="text-green-400" />
                      Drift Vectors
                    </h3>

                    {sortedDrifts.length === 0 ? (
                      <p className="text-xs text-zinc-600">
                        {driftData.slices.length < 2
                          ? "Need at least 2 time slices to compute drift. Add more fragments across different time periods."
                          : "No significant drift detected between slices."}
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {sortedDrifts.map((drift, i) => (
                          <div
                            key={i}
                            className="bg-zinc-900 border border-zinc-800 rounded-lg p-3"
                          >
                            <div className="flex items-start justify-between gap-2 mb-2">
                              <p className="text-xs text-zinc-300 flex-1 leading-relaxed">
                                &ldquo;{drift.fragment_text}&rdquo;
                              </p>
                              <div className="flex items-center gap-1 shrink-0">
                                {DRIFT_ICONS[drift.drift_type]}
                                <span
                                  className="text-xs font-medium"
                                  style={{ color: DRIFT_COLORS[drift.drift_type] }}
                                >
                                  {drift.drift_type}
                                </span>
                              </div>
                            </div>

                            {/* Mass bar comparison */}
                            <div className="space-y-1">
                              <div className="flex items-center gap-2">
                                <span className="text-[10px] text-zinc-600 w-6">t1</span>
                                <div className="flex-1 h-2 bg-zinc-800 rounded overflow-hidden">
                                  <div
                                    className="h-full bg-zinc-500 rounded transition-all"
                                    style={{
                                      width: `${(drift.mass_t1 / maxMass) * 100}%`,
                                    }}
                                  />
                                </div>
                                <span className="text-[10px] text-zinc-500 w-10 text-right font-mono">
                                  {drift.mass_t1.toFixed(3)}
                                </span>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="text-[10px] text-zinc-600 w-6">t2</span>
                                <div className="flex-1 h-2 bg-zinc-800 rounded overflow-hidden">
                                  <div
                                    className="h-full rounded transition-all"
                                    style={{
                                      width: `${(drift.mass_t2 / maxMass) * 100}%`,
                                      backgroundColor: DRIFT_COLORS[drift.drift_type],
                                    }}
                                  />
                                </div>
                                <span className="text-[10px] font-mono w-10 text-right" style={{ color: DRIFT_COLORS[drift.drift_type] }}>
                                  {drift.mass_t2.toFixed(3)}
                                </span>
                              </div>
                            </div>

                            {/* Metadata row */}
                            <div className="flex items-center gap-3 mt-2">
                              {drift.domain && (
                                <span
                                  className="text-[10px] px-1.5 py-0.5 rounded"
                                  style={{
                                    backgroundColor:
                                      (DOMAIN_COLORS[drift.domain] || "#71717a") + "20",
                                    color: DOMAIN_COLORS[drift.domain] || "#71717a",
                                  }}
                                >
                                  {drift.domain}
                                </span>
                              )}
                              <span className="text-[10px] text-zinc-600">
                                {drift.mass_delta > 0 ? "+" : ""}
                                {drift.mass_delta.toFixed(4)} mass
                              </span>
                              {drift.was_hub_t1 && (
                                <span className="text-[10px] text-cyan-600">hub@t1</span>
                              )}
                              {drift.is_hub_t2 && (
                                <span className="text-[10px] text-cyan-400">hub@t2</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
