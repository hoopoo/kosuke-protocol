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

export interface Stats {
  fragments: number;
  reflections: number;
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
};
