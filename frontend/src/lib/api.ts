const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8070';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export interface Project {
  id: string;
  name: string;
  query: string;
  query_model?: Record<string, unknown>;
  geography?: Record<string, unknown>;
  languages?: string[];
  audience?: string[];
  intent?: string[];
  source_types?: string[];
  scoring_profile: string;
  max_discovery_depth: number;
  max_sources: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface DiscoveryRun {
  id: string;
  project_id: string;
  status: string;
  current_stage?: string;
  progress: number;
  stats?: Record<string, unknown>;
  error?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface Source {
  id: string;
  telegram_id?: number;
  username?: string;
  title?: string;
  description?: string;
  source_type?: string;
  member_count?: number;
  status: string;
  topic_analysis?: Record<string, unknown>;
  language_analysis?: Record<string, unknown>;
  geography_analysis?: Record<string, unknown>;
  audience_analysis?: Record<string, unknown>;
  intent_analysis?: Record<string, unknown>;
  activity_analysis?: Record<string, unknown>;
  first_seen_at: string;
  last_analyzed_at?: string;
}

export interface SourceWithScore {
  source: {
    id: string;
    telegram_id?: number;
    username?: string;
    title?: string;
    source_type?: string;
    member_count?: number;
    status: string;
  };
  score: {
    total: number;
    breakdown: Record<string, number>;
    profile: string;
  };
}

export interface ScoringProfile {
  id: string;
  name: string;
  weights: Record<string, number>;
  description?: string;
  is_default: boolean;
  created_at: string;
}

export interface Stats {
  total_sources: number;
  total_projects: number;
  total_runs: number;
  sources_by_status: Record<string, number>;
  avg_score?: number;
}

export interface GraphData {
  nodes: Array<{ id: string; label: string; size: number; color: string; score?: number }>;
  edges: Array<{ source: string; target: string; edge_type: string; confidence: number }>;
}

export const api = {
  projects: {
    list: () => request<Project[]>('/api/projects'),
    get: (id: string) => request<Project>(`/api/projects/${id}`),
    create: (data: { name: string; query: string; scoring_profile?: string }) =>
      request<Project>('/api/projects', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: Partial<Project>) =>
      request<Project>(`/api/projects/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id: string) =>
      request<{ ok: boolean }>(`/api/projects/${id}`, { method: 'DELETE' }),
  },

  discovery: {
    start: (projectId: string) =>
      request<DiscoveryRun>(`/api/projects/${projectId}/discover`, { method: 'POST' }),
    listRuns: (projectId: string) =>
      request<DiscoveryRun[]>(`/api/projects/${projectId}/runs`),
    getRun: (runId: string) => request<DiscoveryRun>(`/api/runs/${runId}`),
    cancelRun: (runId: string) =>
      request<{ ok: boolean }>(`/api/runs/${runId}/cancel`, { method: 'POST' }),
  },

  sources: {
    listForProject: (projectId: string, params?: {
      min_score?: number;
      max_score?: number;
      source_type?: string;
      status?: string;
      sort_by?: string;
      limit?: number;
      offset?: number;
    }) => {
      const qs = new URLSearchParams();
      if (params) Object.entries(params).forEach(([k, v]) => { if (v !== undefined) qs.set(k, String(v)); });
      return request<SourceWithScore[]>(`/api/projects/${projectId}/sources?${qs}`);
    },
    get: (id: string) => request<Source>(`/api/sources/${id}`),
    getScore: (id: string, projectId: string) =>
      request<{ total: number; breakdown: Record<string, number>; profile: string }>(
        `/api/sources/${id}/score?project_id=${projectId}`
      ),
    getRelated: (id: string) => request<Source[]>(`/api/sources/${id}/related`),
    review: (id: string, projectId: string, action: 'approve' | 'reject' | 'skip', reason?: string) =>
      request<any>(`/api/sources/${id}/review?project_id=${projectId}`, {
        method: 'POST',
        body: JSON.stringify({ action, reason }),
      }),
  },

  scoring: {
    listProfiles: () => request<ScoringProfile[]>('/api/scoring-profiles'),
  },

  graph: {
    get: (projectId: string) => request<GraphData>(`/api/projects/${projectId}/graph`),
  },

  export: {
    sources: (projectId: string, format: 'json' | 'csv' = 'json', minScore = 0) =>
      request<any>(`/api/projects/${projectId}/export?format=${format}&min_score=${minScore}`),
  },

  stats: {
    get: () => request<Stats>('/api/stats'),
  },
};
