import { useState } from "react";
import { api, type Fragment } from "@/lib/api";
import { Plus, Upload, Trash2, Tag, Globe, User } from "lucide-react";

const DOMAINS = [
  "philosophy", "technology", "art", "science", "urban",
  "body", "nature", "politics", "economics", "culture",
  "psychology", "literature", "music", "spirituality", "mathematics",
];

interface Props {
  fragments: Fragment[];
  onRefresh: () => void;
}

export function FragmentPanel({ fragments, onRefresh }: Props) {
  const [text, setText] = useState("");
  const [source, setSource] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [domain, setDomain] = useState("");
  const [author, setAuthor] = useState("");
  const [mode, setMode] = useState<"single" | "ingest">("single");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setError("");
    try {
      const tags = tagsInput
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      if (mode === "single") {
        await api.createFragment(text, source || "manual", tags, domain || undefined, author || undefined);
      } else {
        await api.ingestText(text, source || "manual", tags, domain || undefined, author || undefined);
      }
      setText("");
      setSource("");
      setTagsInput("");
      setDomain("");
      setAuthor("");
      onRefresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add fragment");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteFragment(id);
      onRefresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete");
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Input area */}
      <div className="border-b border-zinc-800 p-4 space-y-3">
        <div className="flex gap-2">
          <button
            onClick={() => setMode("single")}
            className={`flex items-center gap-1 px-3 py-1.5 text-xs rounded-md transition-colors ${
              mode === "single"
                ? "bg-zinc-100 text-zinc-900"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <Plus size={14} /> Fragment
          </button>
          <button
            onClick={() => setMode("ingest")}
            className={`flex items-center gap-1 px-3 py-1.5 text-xs rounded-md transition-colors ${
              mode === "ingest"
                ? "bg-zinc-100 text-zinc-900"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <Upload size={14} /> Ingest Text
          </button>
        </div>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={
            mode === "single"
              ? "Enter a fragment of thought..."
              : "Paste longer text to be chunked into fragments..."
          }
          className="w-full bg-zinc-900 border border-zinc-700 rounded-md p-3 text-sm text-zinc-100 placeholder-zinc-600 resize-none focus:outline-none focus:border-zinc-500 transition-colors"
          rows={mode === "single" ? 3 : 6}
        />

        <div className="flex gap-2">
          <input
            value={source}
            onChange={(e) => setSource(e.target.value)}
            placeholder="Source (e.g., essay, observation)"
            className="flex-1 bg-zinc-900 border border-zinc-700 rounded-md px-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-500"
          />
          <input
            value={tagsInput}
            onChange={(e) => setTagsInput(e.target.value)}
            placeholder="Tags (comma-separated)"
            className="flex-1 bg-zinc-900 border border-zinc-700 rounded-md px-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-500"
          />
        </div>

        <div className="flex gap-2">
          <select
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            className="flex-1 bg-zinc-900 border border-zinc-700 rounded-md px-3 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-zinc-500"
          >
            <option value="">Domain (optional)</option>
            {DOMAINS.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
          <input
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            placeholder="Author (optional)"
            className="flex-1 bg-zinc-900 border border-zinc-700 rounded-md px-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-500"
          />
        </div>

        <button
          onClick={handleSubmit}
          disabled={loading || !text.trim()}
          className="w-full bg-zinc-100 text-zinc-900 py-2 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading
            ? "Processing..."
            : mode === "single"
            ? "Add Fragment"
            : "Ingest & Chunk"}
        </button>

        {error && (
          <p className="text-red-400 text-xs">{error}</p>
        )}
      </div>

      {/* Fragment list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {fragments.length === 0 ? (
          <div className="text-center text-zinc-600 py-12">
            <p className="text-sm">No fragments yet</p>
            <p className="text-xs mt-1">Add fragments to begin exploring</p>
          </div>
        ) : (
          fragments.map((frag) => (
            <div
              key={frag.id}
              className="group bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 hover:border-zinc-700 transition-colors"
            >
              <p className="text-sm text-zinc-200 leading-relaxed">
                {frag.text}
              </p>
              <div className="flex items-center justify-between mt-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs text-zinc-600">{frag.source}</span>
                  {frag.author && (
                    <span className="inline-flex items-center gap-0.5 text-xs text-violet-400/80 bg-violet-500/10 border border-violet-500/20 px-1.5 py-0.5 rounded">
                      <User size={10} />
                      {frag.author}
                    </span>
                  )}
                  {frag.domain && (
                    <span className="inline-flex items-center gap-0.5 text-xs text-emerald-400/80 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded">
                      <Globe size={10} />
                      {frag.domain}
                    </span>
                  )}
                  {frag.tags.filter(Boolean).map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center gap-0.5 text-xs text-zinc-500 bg-zinc-800 px-1.5 py-0.5 rounded"
                    >
                      <Tag size={10} />
                      {tag}
                    </span>
                  ))}
                </div>
                <button
                  onClick={() => handleDelete(frag.id)}
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
