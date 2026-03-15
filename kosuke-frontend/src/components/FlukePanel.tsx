import { useState } from "react";
import { api, type FlukeResult } from "@/lib/api";
import { Sparkles, RotateCw } from "lucide-react";

interface Props {
  onReflect: (fluke: FlukeResult) => void;
  fragmentCount: number;
}

export function FlukePanel({ onReflect, fragmentCount }: Props) {
  const [query, setQuery] = useState("");
  const [fluke, setFluke] = useState<FlukeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const generateFluke = async () => {
    setLoading(true);
    setError("");
    try {
      const result = await api.generateFluke(
        query.trim() || undefined,
        Math.min(fragmentCount, 20)
      );
      setFluke(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate fluke");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Controls */}
      <div className="border-b border-zinc-800 p-4 space-y-3">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Optional: What are you exploring? (provides context for the fluke)"
          className="w-full bg-zinc-900 border border-zinc-700 rounded-md p-3 text-sm text-zinc-100 placeholder-zinc-600 resize-none focus:outline-none focus:border-zinc-500 transition-colors"
          rows={2}
        />
        <button
          onClick={generateFluke}
          disabled={loading || fragmentCount < 2}
          className="w-full bg-amber-500/90 text-zinc-900 py-2.5 rounded-md text-sm font-medium hover:bg-amber-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <RotateCw size={16} className="animate-spin" /> Generating...
            </>
          ) : (
            <>
              <Sparkles size={16} /> Generate Fluke
            </>
          )}
        </button>
        {fragmentCount < 2 && (
          <p className="text-zinc-600 text-xs text-center">
            Add at least 2 fragments to generate flukes
          </p>
        )}
        {error && <p className="text-red-400 text-xs">{error}</p>}
      </div>

      {/* Fluke result */}
      <div className="flex-1 overflow-y-auto p-4">
        {fluke ? (
          <div className="space-y-6">
            {/* Fragment A */}
            <div className="space-y-1">
              <p className="text-xs text-zinc-500 uppercase tracking-wider font-medium">
                Fragment A
              </p>
              <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
                <p className="text-sm text-zinc-200 leading-relaxed italic">
                  "{fluke.fragment_a.text}"
                </p>
                <p className="text-xs text-zinc-600 mt-2">
                  {fluke.fragment_a.source}
                </p>
              </div>
            </div>

            {/* Connection line */}
            <div className="flex items-center justify-center">
              <div className="h-px flex-1 bg-gradient-to-r from-transparent via-amber-500/30 to-transparent" />
              <span className="px-3 text-xs text-amber-500/70">
                distance: {fluke.distance.toFixed(2)}
              </span>
              <div className="h-px flex-1 bg-gradient-to-r from-transparent via-amber-500/30 to-transparent" />
            </div>

            {/* Fragment B */}
            <div className="space-y-1">
              <p className="text-xs text-zinc-500 uppercase tracking-wider font-medium">
                Fragment B
              </p>
              <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
                <p className="text-sm text-zinc-200 leading-relaxed italic">
                  "{fluke.fragment_b.text}"
                </p>
                <p className="text-xs text-zinc-600 mt-2">
                  {fluke.fragment_b.source}
                </p>
              </div>
            </div>

            {/* Tension */}
            <div className="bg-amber-500/5 border border-amber-500/20 rounded-lg p-4 space-y-2">
              <p className="text-xs text-amber-500/70 uppercase tracking-wider font-medium">
                Tension
              </p>
              <p className="text-sm text-zinc-200 leading-relaxed">
                {fluke.tension}
              </p>
            </div>

            {/* Reflection Prompt */}
            <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4 space-y-2">
              <p className="text-xs text-zinc-500 uppercase tracking-wider font-medium">
                Reflection Prompt
              </p>
              <p className="text-base text-zinc-100 leading-relaxed font-medium">
                {fluke.reflection_prompt}
              </p>
            </div>

            {/* Scores */}
            <div className="grid grid-cols-4 gap-2">
              {[
                { label: "Fluke", value: fluke.fluke_score },
                { label: "Distance", value: fluke.distance },
                { label: "Resonance", value: fluke.core_resonance },
                { label: "Tension", value: fluke.tension_score },
              ].map((s) => (
                <div
                  key={s.label}
                  className="text-center bg-zinc-900/50 border border-zinc-800 rounded-md p-2"
                >
                  <p className="text-lg font-mono text-zinc-200">
                    {s.value.toFixed(2)}
                  </p>
                  <p className="text-xs text-zinc-600">{s.label}</p>
                </div>
              ))}
            </div>

            {/* Reflect button */}
            <button
              onClick={() => onReflect(fluke)}
              className="w-full bg-zinc-100 text-zinc-900 py-2 rounded-md text-sm font-medium hover:bg-white transition-colors"
            >
              Write Reflection
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center text-zinc-600 py-12">
            <Sparkles size={32} className="mb-3 text-zinc-700" />
            <p className="text-sm">No fluke generated yet</p>
            <p className="text-xs mt-1">
              Generate a fluke to discover unexpected connections
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
