import { useState, useEffect, useCallback } from "react";
import "./App.css";
import { api, type Fragment, type Reflection, type FlukeResult } from "@/lib/api";
import { FragmentPanel } from "@/components/FragmentPanel";
import { FlukePanel } from "@/components/FlukePanel";
import { ReflectionPanel } from "@/components/ReflectionPanel";
import { NetworkPanel } from "@/components/NetworkPanel";
import { DriftPanel } from "@/components/DriftPanel";
import { Layers, Sparkles, PenLine, Network, Clock } from "lucide-react";

type Tab = "fragments" | "flukes" | "reflections" | "network" | "drift";

function App() {
  const [tab, setTab] = useState<Tab>("fragments");
  const [fragments, setFragments] = useState<Fragment[]>([]);
  const [reflections, setReflections] = useState<Reflection[]>([]);
  const [activeFluke, setActiveFluke] = useState<FlukeResult | null>(null);
  const [stats, setStats] = useState({ fragments: 0, reflections: 0 });

  const loadFragments = useCallback(async () => {
    try {
      const data = await api.getFragments();
      setFragments(data);
    } catch {
      /* ignore */
    }
  }, []);

  const loadReflections = useCallback(async () => {
    try {
      const data = await api.getReflections();
      setReflections(data);
    } catch {
      /* ignore */
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const data = await api.getStats();
      setStats(data);
    } catch {
      /* ignore */
    }
  }, []);

  const refreshAll = useCallback(() => {
    loadFragments();
    loadReflections();
    loadStats();
  }, [loadFragments, loadReflections, loadStats]);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  const handleReflect = (fluke: FlukeResult) => {
    setActiveFluke(fluke);
    setTab("reflections");
  };

  const tabs: { id: Tab; label: string; icon: React.ReactNode; count: number }[] = [
    { id: "fragments", label: "Fragments", icon: <Layers size={16} />, count: stats.fragments },
    { id: "flukes", label: "Flukes", icon: <Sparkles size={16} />, count: 0 },
    { id: "reflections", label: "Reflections", icon: <PenLine size={16} />, count: stats.reflections },
    { id: "network", label: "Network", icon: <Network size={16} />, count: stats.edges || 0 },
    { id: "drift", label: "Drift", icon: <Clock size={16} />, count: 0 },
  ];

  return (
    <div className="h-screen bg-zinc-950 text-zinc-100 flex flex-col">
      {/* Header */}
      <header className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">
            Kosuke Protocol
          </h1>
          <p className="text-xs text-zinc-500 mt-0.5">
            An Intelligence Ecosystem for Meaning Generation
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs text-zinc-600">
          <span>{stats.fragments} fragments</span>
          <span>{stats.reflections} reflections</span>
        </div>
      </header>

      {/* Tab navigation */}
      <nav className="border-b border-zinc-800 px-6 flex gap-1 shrink-0">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-3 text-sm border-b-2 transition-colors ${
              tab === t.id
                ? "border-zinc-100 text-zinc-100"
                : "border-transparent text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {t.icon}
            {t.label}
            {t.count > 0 && (
              <span className="bg-zinc-800 text-zinc-400 text-xs px-1.5 py-0.5 rounded-full">
                {t.count}
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main className="flex-1 overflow-hidden">
        {tab === "fragments" && (
          <FragmentPanel fragments={fragments} onRefresh={refreshAll} />
        )}
        {tab === "flukes" && (
          <FlukePanel
            onReflect={handleReflect}
            fragmentCount={stats.fragments}
          />
        )}
        {tab === "reflections" && (
          <ReflectionPanel
            reflections={reflections}
            activeFluke={activeFluke}
            onRefresh={refreshAll}
          />
        )}
        {tab === "network" && (
          <NetworkPanel fragmentCount={stats.fragments} />
        )}
        {tab === "drift" && <DriftPanel />}
      </main>
    </div>
  );
}

export default App;
