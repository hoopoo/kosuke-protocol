import { useState, useEffect, useCallback } from "react";
import { api, type MeaningWeather } from "@/lib/api";
import {
  Cloud,
  Wind,
  Zap,
  CloudRain,
  Sun,
  RefreshCw,
  Activity,
  BarChart3,
  Layers,
  Orbit,
  Sparkles,
} from "lucide-react";

const WEATHER_CONFIG: Record<
  string,
  { icon: React.ReactNode; color: string; bg: string; description: string }
> = {
  calm: {
    icon: <Sun size={32} />,
    color: "text-amber-400",
    bg: "bg-amber-400/10",
    description: "Meaning structures are stable. A quiet period for reflection.",
  },
  breeze: {
    icon: <Wind size={32} />,
    color: "text-sky-400",
    bg: "bg-sky-400/10",
    description: "Gentle shifts in the network. New connections are forming slowly.",
  },
  active: {
    icon: <Cloud size={32} />,
    color: "text-emerald-400",
    bg: "bg-emerald-400/10",
    description: "Active meaning formation. Clusters and hubs are evolving.",
  },
  storm: {
    icon: <CloudRain size={32} />,
    color: "text-violet-400",
    bg: "bg-violet-400/10",
    description: "Rapid structural changes. New galaxies and hubs are emerging.",
  },
  turbulence: {
    icon: <Zap size={32} />,
    color: "text-red-400",
    bg: "bg-red-400/10",
    description: "Extreme volatility. The meaning landscape is being reshaped.",
  },
};

function VolatilityBar({
  label,
  value,
  icon,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
}) {
  const pct = Math.round(value * 100);
  const barColor =
    pct < 20
      ? "bg-amber-400"
      : pct < 40
        ? "bg-sky-400"
        : pct < 60
          ? "bg-emerald-400"
          : pct < 80
            ? "bg-violet-400"
            : "bg-red-400";

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-2 text-zinc-400">
          {icon}
          {label}
        </span>
        <span className="text-zinc-300 font-mono">{pct}%</span>
      </div>
      <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: number | string;
  icon: React.ReactNode;
}) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 flex items-center gap-3">
      <div className="text-zinc-500">{icon}</div>
      <div>
        <div className="text-lg font-semibold text-zinc-100">{value}</div>
        <div className="text-xs text-zinc-500">{label}</div>
      </div>
    </div>
  );
}

export function WeatherPanel() {
  const [weather, setWeather] = useState<MeaningWeather | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchWeather = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMeaningWeather();
      setWeather(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch weather");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWeather();
  }, [fetchWeather]);

  if (loading && !weather) {
    return (
      <div className="h-full flex items-center justify-center text-zinc-500">
        <RefreshCw size={20} className="animate-spin mr-2" />
        Reading the meaning atmosphere...
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-zinc-500 gap-3">
        <p className="text-red-400">{error}</p>
        <button
          onClick={fetchWeather}
          className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded text-sm transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!weather) return null;

  const config = WEATHER_CONFIG[weather.weather] || WEATHER_CONFIG.calm;

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      {/* Header with refresh */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-zinc-100">
          Meaning Weather
        </h2>
        <button
          onClick={fetchWeather}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 rounded text-sm text-zinc-300 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Weather state hero */}
      <div
        className={`${config.bg} border border-zinc-800 rounded-xl p-8 flex flex-col items-center text-center space-y-4`}
      >
        <div className={config.color}>{config.icon}</div>
        <div>
          <h3
            className={`text-3xl font-bold capitalize tracking-tight ${config.color}`}
          >
            {weather.weather}
          </h3>
          <p className="text-zinc-400 text-sm mt-2 max-w-md">
            {config.description}
          </p>
        </div>
        <div className="flex items-center gap-2 mt-2">
          <span className="text-xs text-zinc-500">Volatility</span>
          <div className="w-48 h-3 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-1000 ${
                weather.volatility < 0.2
                  ? "bg-amber-400"
                  : weather.volatility < 0.4
                    ? "bg-sky-400"
                    : weather.volatility < 0.6
                      ? "bg-emerald-400"
                      : weather.volatility < 0.8
                        ? "bg-violet-400"
                        : "bg-red-400"
              }`}
              style={{ width: `${Math.round(weather.volatility * 100)}%` }}
            />
          </div>
          <span className="text-sm font-mono text-zinc-300">
            {Math.round(weather.volatility * 100)}%
          </span>
        </div>
        {!weather.snapshot_exists && (
          <p className="text-xs text-zinc-600 mt-1">
            First reading - no previous snapshot to compare against
          </p>
        )}
      </div>

      {/* Volatility breakdown */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-6 space-y-5">
        <h4 className="text-sm font-medium text-zinc-300">
          Volatility Breakdown
        </h4>
        <VolatilityBar
          label="New Edge Rate"
          value={weather.new_edge_rate}
          icon={<Activity size={14} />}
        />
        <VolatilityBar
          label="Cluster Shift"
          value={weather.cluster_shift}
          icon={<Layers size={14} />}
        />
        <VolatilityBar
          label="Gravity Change"
          value={weather.gravity_change}
          icon={<Orbit size={14} />}
        />
        <VolatilityBar
          label="Galaxy Shift"
          value={weather.galaxy_shift}
          icon={<Sparkles size={14} />}
        />
      </div>

      {/* Network stats */}
      <div>
        <h4 className="text-sm font-medium text-zinc-300 mb-3">
          Current Network
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <MetricCard
            label="Fragments"
            value={weather.total_fragments}
            icon={<Layers size={16} />}
          />
          <MetricCard
            label="Edges"
            value={weather.total_edges}
            icon={<Activity size={16} />}
          />
          <MetricCard
            label="New Edges"
            value={weather.new_edges}
            icon={<Zap size={16} />}
          />
          <MetricCard
            label="Gravity Hubs"
            value={weather.total_hubs}
            icon={<Orbit size={16} />}
          />
          <MetricCard
            label="Galaxies"
            value={weather.total_galaxies}
            icon={<Sparkles size={16} />}
          />
        </div>
      </div>

      {/* Weather scale legend */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-6">
        <h4 className="text-sm font-medium text-zinc-300 mb-4">
          Weather Scale
        </h4>
        <div className="flex flex-col gap-3">
          {Object.entries(WEATHER_CONFIG).map(([key, cfg]) => (
            <div
              key={key}
              className={`flex items-center gap-3 text-sm ${
                weather.weather === key
                  ? `${cfg.color} font-medium`
                  : "text-zinc-500"
              }`}
            >
              <div className="w-5 flex-shrink-0">{cfg.icon}</div>
              <span className="capitalize w-24">{key}</span>
              <span className="text-xs">
                {key === "calm" && "< 15%"}
                {key === "breeze" && "15-35%"}
                {key === "active" && "35-55%"}
                {key === "storm" && "55-75%"}
                {key === "turbulence" && "> 75%"}
              </span>
              {weather.weather === key && (
                <BarChart3 size={14} className={cfg.color} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Window info */}
      <p className="text-xs text-zinc-600 text-center">
        Analyzing edges created in the last {weather.window_hours}h window
        {weather.snapshot_exists
          ? " · Comparing against previous snapshot"
          : " · First snapshot recorded"}
      </p>
    </div>
  );
}
