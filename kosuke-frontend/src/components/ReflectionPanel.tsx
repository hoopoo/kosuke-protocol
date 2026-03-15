import { useState } from "react";
import { api, type Reflection, type FlukeResult } from "@/lib/api";
import { PenLine, Trash2, Download } from "lucide-react";

interface Props {
  reflections: Reflection[];
  activeFluke: FlukeResult | null;
  onRefresh: () => void;
}

export function ReflectionPanel({ reflections, activeFluke, onRefresh }: Props) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setError("");
    try {
      const linkedIds: string[] = [];
      let tension: string | undefined;
      if (activeFluke) {
        linkedIds.push(activeFluke.fragment_a.id, activeFluke.fragment_b.id);
        tension = activeFluke.tension;
      }
      await api.createReflection(text, linkedIds, tension);
      setText("");
      onRefresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save reflection");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteReflection(id);
      onRefresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete");
    }
  };

  const handleExport = async () => {
    try {
      const md = await api.exportMarkdown();
      const blob = new Blob([md], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "kosuke-protocol-living-book.md";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Writing area */}
      <div className="border-b border-zinc-800 p-4 space-y-3">
        {activeFluke && (
          <div className="bg-amber-500/5 border border-amber-500/20 rounded-md p-3">
            <p className="text-xs text-amber-500/70 mb-1">Reflecting on:</p>
            <p className="text-sm text-zinc-300 italic">
              {activeFluke.reflection_prompt}
            </p>
          </div>
        )}

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Write your reflection..."
          className="w-full bg-zinc-900 border border-zinc-700 rounded-md p-3 text-sm text-zinc-100 placeholder-zinc-600 resize-none focus:outline-none focus:border-zinc-500 transition-colors"
          rows={6}
        />

        <div className="flex gap-2">
          <button
            onClick={handleSubmit}
            disabled={loading || !text.trim()}
            className="flex-1 bg-zinc-100 text-zinc-900 py-2 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            <PenLine size={14} />
            {loading ? "Saving..." : "Save Reflection"}
          </button>
          <button
            onClick={handleExport}
            className="bg-zinc-800 text-zinc-300 px-4 py-2 rounded-md text-sm hover:bg-zinc-700 transition-colors flex items-center gap-2"
          >
            <Download size={14} /> Export
          </button>
        </div>

        {error && <p className="text-red-400 text-xs">{error}</p>}
      </div>

      {/* Reflection list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {reflections.length === 0 ? (
          <div className="text-center text-zinc-600 py-12">
            <PenLine size={24} className="mx-auto mb-2 text-zinc-700" />
            <p className="text-sm">No reflections yet</p>
            <p className="text-xs mt-1">
              Generate a fluke and write your thoughts
            </p>
          </div>
        ) : (
          reflections.map((ref) => (
            <div
              key={ref.id}
              className="group bg-zinc-900/50 border border-zinc-800 rounded-lg p-4 hover:border-zinc-700 transition-colors"
            >
              <p className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap">
                {ref.text}
              </p>
              <div className="flex items-center justify-between mt-3 pt-2 border-t border-zinc-800/50">
                <div>
                  {ref.linked_fluke_tension && (
                    <p className="text-xs text-zinc-600 italic">
                      Re: {ref.linked_fluke_tension}
                    </p>
                  )}
                  <p className="text-xs text-zinc-700">
                    {new Date(ref.timestamp).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={() => handleDelete(ref.id)}
                  className="opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-red-400 transition-all"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
