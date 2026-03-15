const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface Fragment {
  id: string;
  text: string;
  source: string;
  timestamp: string;
  tags: string[];
}

export interface FlukeResult {
  fragment_a: Fragment;
  fragment_b: Fragment;
  distance: number;
  core_resonance: number;
  tension_score: number;
  context_fit: number;
  fluke_score: number;
  tension: string;
  reflection_prompt: string;
}

export interface Reflection {
  id: string;
  text: string;
  linked_fragment_ids: string[];
  linked_fluke_tension: string | null;
  timestamp: string;
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
  createFragment: (text: string, source: string, tags: string[]) =>
    request<Fragment>("/fragments", {
      method: "POST",
      body: JSON.stringify({ text, source, tags }),
    }),
  ingestText: (text: string, source: string, tags: string[]) =>
    request<Fragment[]>("/fragments/ingest", {
      method: "POST",
      body: JSON.stringify({ text, source, tags }),
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
  generateFluke: (query?: string, nCandidates = 10) =>
    request<FlukeResult>("/fluke", {
      method: "POST",
      body: JSON.stringify({ query, n_candidates: nCandidates }),
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
