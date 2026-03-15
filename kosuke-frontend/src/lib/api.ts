const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface Fragment {
  id: string;
  text: string;
  source: string;
  timestamp: string;
  tags: string[];
  domain: string | null;
}

export interface FlukeResult {
  fragment_a: Fragment;
  fragment_b: Fragment;
  distance: number;
  core_resonance: number;
  tension_score: number;
  context_fit: number;
  domain_crossing: number;
  fluke_score: number;
  tension: string;
  reflection_prompt: string;
  generation_method: "standard" | "serendipity" | "domain_cross";
}

export interface SlowModeStatus {
  enabled: boolean;
  flukes_remaining: number;
  flukes_generated: number;
  max_flukes: number;
  cooldown_active: boolean;
  message: string | null;
}

export interface Reflection {
  id: string;
  text: string;
  linked_fragment_ids: string[];
  linked_fluke_tension: string | null;
  timestamp: string;
}

export interface SlowModeConfig {
  enabled: boolean;
  max_flukes_per_session: number;
  cooldown_message: string;
}

export interface NetworkNode {
  id: string;
  text: string;
  domain: string | null;
  type: string;
  is_boundary: boolean;
  meaning_mass: number;
  is_gravity_hub: boolean;
  cluster_id: number | null;
  is_galaxy_center: boolean;
}

export interface NetworkEdge {
  source: string;
  target: string;
  weight: number;
  relation: string;
}

export interface NetworkData {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

export interface NetworkMetrics {
  fragments: number;
  edges: number;
  clusters: number;
  boundary_nodes: number;
  gravity_hubs: number;
  galaxy_count: number;
  largest_galaxy: number;
  average_cluster_size: number;
}

export interface ClusterInfo {
  cluster_id: number;
  size: number;
  density: number;
  domain_entropy: number;
  center_fragment: string;
  is_galaxy: boolean;
  member_ids: string[];
}

export interface GalaxyData {
  clusters: ClusterInfo[];
  galaxies: ClusterInfo[];
  galaxy_count: number;
  largest_galaxy: number;
  average_cluster_size: number;
}

export interface TimeSliceMetrics {
  slice_label: string;
  start_time: string;
  end_time: string;
  fragment_count: number;
  edge_count: number;
  cluster_count: number;
  galaxy_count: number;
  gravity_hub_count: number;
  hub_ids: string[];
  galaxy_centers: string[];
  meaning_mass_map: Record<string, number>;
}

export interface DriftVector {
  fragment_id: string;
  fragment_text: string;
  domain: string | null;
  mass_t1: number;
  mass_t2: number;
  mass_delta: number;
  was_hub_t1: boolean;
  is_hub_t2: boolean;
  drift_type: "emergence" | "migration" | "collapse" | "stable";
}

export interface DriftAnalysis {
  slices: TimeSliceMetrics[];
  drift_vectors: DriftVector[];
  emergence_count: number;
  migration_count: number;
  collapse_count: number;
  stable_count: number;
  slice_mode: string;
}

export interface TopConcept {
  fragment_id: string;
  text: string;
  domain: string | null;
  meaning_mass: number;
  is_gravity_hub: boolean;
  is_galaxy_center: boolean;
  edge_count: number;
  mass_trend: number;
}

export interface TopConceptsResult {
  concepts: TopConcept[];
  total_fragments: number;
}

export interface GalaxyWatch {
  cluster_id: number;
  size: number;
  density: number;
  domain_entropy: number;
  center_fragment_id: string;
  center_fragment_text: string;
  center_domain: string | null;
  member_domains: string[];
  growth: number;
}

export interface GalaxyWatchResult {
  galaxies: GalaxyWatch[];
  total_galaxies: number;
}

export interface ReflectionImpact {
  reflection_id: string;
  reflection_text: string;
  timestamp: string;
  linked_fragment_count: number;
  edges_created: number;
  mass_boost: number;
  clusters_touched: number;
  galaxies_touched: number;
}

export interface ReflectionImpactResult {
  reflections: ReflectionImpact[];
  total_reflections: number;
  avg_edges_created: number;
  avg_mass_boost: number;
}

export interface DomainStat {
  domain: string;
  fragment_count: number;
  percentage: number;
  edge_count: number;
  avg_meaning_mass: number;
  hub_count: number;
}

export interface DomainBalanceResult {
  domains: DomainStat[];
  total_fragments: number;
  underrepresented: string[];
  dominant: string[];
}

export interface EmergingSignal {
  fragment_id: string;
  text: string;
  domain: string | null;
  current_mass: number;
  mass_change: number;
  is_domain_crossing: boolean;
  is_reflection_linked: boolean;
  signal_strength: number;
}

export interface EmergingSignalsResult {
  signals: EmergingSignal[];
  total_signals: number;
}

export interface Stats {
  fragments: number;
  reflections: number;
  edges: number;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

async function requestText(path: string, options?: RequestInit): Promise<string> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error("Request failed");
  }
  return res.text();
}

export const api = {
  getStats: () => request<Stats>("/stats"),

  // Fragments
  getFragments: (limit = 100, offset = 0) =>
    request<Fragment[]>(`/fragments?limit=${limit}&offset=${offset}`),
  createFragment: (text: string, source: string, tags: string[], domain?: string) =>
    request<Fragment>("/fragments", {
      method: "POST",
      body: JSON.stringify({ text, source, tags, domain: domain || null }),
    }),
  ingestText: (text: string, source: string, tags: string[], domain?: string) =>
    request<Fragment[]>("/fragments/ingest", {
      method: "POST",
      body: JSON.stringify({ text, source, tags, domain: domain || null }),
    }),
  deleteFragment: (id: string) =>
    request<{ status: string }>(`/fragments/${id}`, { method: "DELETE" }),

  // Sampling
  sample: (method: string, n: number, query?: string, tags?: string[]) =>
    request<Fragment[]>("/sample", {
      method: "POST",
      body: JSON.stringify({ method, n, query, tags }),
    }),

  // Fluke
  generateFluke: (query?: string, nCandidates = 10, sessionId?: string) =>
    request<FlukeResult>("/fluke", {
      method: "POST",
      body: JSON.stringify({ query, n_candidates: nCandidates, session_id: sessionId }),
    }),

  // Slow Mode
  getSlowModeStatus: (sessionId = "default") =>
    request<SlowModeStatus>(`/slow-mode/status?session_id=${sessionId}`),
  resetSlowMode: (sessionId = "default") =>
    request<SlowModeStatus>(`/slow-mode/reset?session_id=${sessionId}`, {
      method: "POST",
    }),
  updateSlowModeConfig: (config: SlowModeConfig) =>
    request<SlowModeConfig>("/slow-mode/config", {
      method: "PUT",
      body: JSON.stringify(config),
    }),

  // Reflections
  getReflections: (limit = 100, offset = 0) =>
    request<Reflection[]>(`/reflections?limit=${limit}&offset=${offset}`),
  createReflection: (
    text: string,
    linkedFragmentIds: string[],
    linkedFlukeTension?: string
  ) =>
    request<Reflection>("/reflections", {
      method: "POST",
      body: JSON.stringify({
        text,
        linked_fragment_ids: linkedFragmentIds,
        linked_fluke_tension: linkedFlukeTension,
      }),
    }),
  deleteReflection: (id: string) =>
    request<{ status: string }>(`/reflections/${id}`, { method: "DELETE" }),

  // Export
  exportMarkdown: (title?: string) =>
    requestText("/export/markdown", {
      method: "POST",
      body: JSON.stringify({
        title: title || "Kosuke Protocol - Living Book",
        include_fragments: true,
        include_reflections: true,
      }),
    }),

  // Network
  getNetwork: () => request<NetworkData>("/network"),
  getNetworkMetrics: () => request<NetworkMetrics>("/network/metrics"),
  generateSemanticEdges: (threshold = 0.82) =>
    request<{ new_edges_created: number; total_edges: number }>(
      `/network/generate-edges?threshold=${threshold}`,
      { method: "POST" }
    ),
  generateGravityEdges: (threshold = 0.5, epsilon = 0.01) =>
    request<{ new_gravity_edges: number; total_edges: number }>(
      `/network/generate-gravity?threshold=${threshold}&epsilon=${epsilon}`,
      { method: "POST" }
    ),
  detectGalaxies: (densityThreshold = 0.3) =>
    request<GalaxyData>(
      `/network/detect-galaxies?density_threshold=${densityThreshold}`,
      { method: "POST" }
    ),

  // Drift
  analyzeDrift: (mode: "monthly" | "quarterly" | "yearly" = "monthly") =>
    request<DriftAnalysis>(
      `/network/drift?mode=${mode}`,
      { method: "POST" }
    ),

  // Observatory
  getTopConcepts: (limit = 20) =>
    request<TopConceptsResult>(`/observatory/top-concepts?limit=${limit}`),
  getGalaxyWatch: () =>
    request<GalaxyWatchResult>("/observatory/galaxies"),
  getReflectionImpact: () =>
    request<ReflectionImpactResult>("/observatory/reflection-impact"),
  getDomainBalance: () =>
    request<DomainBalanceResult>("/observatory/domain-balance"),
  getEmergingSignals: (limit = 20) =>
    request<EmergingSignalsResult>(`/observatory/emerging-signals?limit=${limit}`),
};
