// API client for GOATAT backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface AnalysisResult {
  id: string;
  filename: string;
  original_filename: string;
  file_size_bytes: number;
  audio_duration_seconds: number;
  sample_rate: number;
  verdict: 'authentic' | 'synthetic' | 'inconclusive';
  confidence: number;
  authentic_probability: number | null;
  synthetic_probability: number | null;
  raw_scores: Record<string, unknown> | null;
  model_name: string;
  model_version: string;
  inference_mode: string;
  inference_time_ms: number;
  is_demo: boolean;
  notes: string | null;
  spectrogram_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface AnalysisListItem {
  id: string;
  original_filename: string;
  verdict: string;
  confidence: number;
  audio_duration_seconds: number;
  model_name: string;
  inference_mode: string;
  is_demo: boolean;
  created_at: string;
}

export interface PaginatedAnalyses {
  items: AnalysisListItem[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface DashboardStats {
  total_analyses: number;
  authentic_count: number;
  synthetic_count: number;
  inconclusive_count: number;
  detection_rate: number | null;
  recent_analyses: AnalysisListItem[];
  suspicious_alerts: number;
  is_demo_data: boolean;
}

export interface HealthResponse {
  status: string;
  database: string;
  model_available: boolean;
  model_name: string;
  model_version: string;
  inference_mode: string;
  environment: string;
  uptime_seconds: number;
  timestamp: string;
}

export interface AlertItem {
  id: string;
  analysis_id: string | null;
  severity: string;
  title: string;
  description: string;
  confidence: number | null;
  acknowledged: boolean;
  dismissed: boolean;
  created_at: string;
  acknowledged_at: string | null;
}

export interface VoiceProfile {
  id: string;
  display_name: string;
  description: string | null;
  has_embedding: boolean;
  consent_given: boolean;
  consent_timestamp: string | null;
  is_experimental: boolean;
  created_at: string;
}

export interface AnalyticsData {
  daily_counts: Array<{ date: string; authentic: number; synthetic: number; inconclusive: number }>;
  verdict_distribution: { authentic: number; synthetic: number; inconclusive: number };
  inference_latency_avg_ms: number;
  score_distribution: unknown[];
  is_demo_data: boolean;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options?.headers || {}),
    },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Health
  health: () => apiFetch<HealthResponse>('/api/v1/health'),

  // Analysis
  analyzeAudio: (file: File, notes?: string) => {
    const form = new FormData();
    form.append('file', file);
    if (notes) form.append('notes', notes);
    return apiFetch<AnalysisResult>('/api/v1/analysis', { method: 'POST', body: form });
  },
  listAnalyses: (params?: { page?: number; per_page?: number; search?: string; verdict?: string }) => {
    const q = new URLSearchParams();
    if (params?.page) q.set('page', String(params.page));
    if (params?.per_page) q.set('per_page', String(params.per_page));
    if (params?.search) q.set('search', params.search);
    if (params?.verdict) q.set('verdict', params.verdict);
    return apiFetch<PaginatedAnalyses>(`/api/v1/analysis?${q}`);
  },
  getAnalysis: (id: string) => apiFetch<AnalysisResult>(`/api/v1/analysis/${id}`),
  deleteAnalysis: (id: string) => apiFetch<{ message: string }>(`/api/v1/analysis/${id}`, { method: 'DELETE' }),

  // Dashboard
  dashboardStats: () => apiFetch<DashboardStats>('/api/v1/dashboard/stats'),
  analytics: (days = 30) => apiFetch<AnalyticsData>(`/api/v1/analytics?days=${days}`),

  // Profiles
  createProfile: (data: FormData) => apiFetch<VoiceProfile>('/api/v1/profiles', { method: 'POST', body: data }),
  listProfiles: () => apiFetch<VoiceProfile[]>('/api/v1/profiles'),
  deleteProfile: (id: string) => apiFetch<{ message: string }>(`/api/v1/profiles/${id}`, { method: 'DELETE' }),
  enrollVoice: (profileId: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return apiFetch<{ message: string }>(`/api/v1/profiles/${profileId}/enroll`, { method: 'POST', body: form });
  },

  // Alerts
  listAlerts: (params?: { severity?: string; acknowledged?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.severity) q.set('severity', params.severity);
    if (params?.acknowledged !== undefined) q.set('acknowledged', String(params.acknowledged));
    return apiFetch<AlertItem[]>(`/api/v1/alerts?${q}`);
  },
  acknowledgeAlert: (id: string) => apiFetch<{ message: string }>(`/api/v1/alerts/${id}/acknowledge`, { method: 'PATCH' }),
  dismissAlert: (id: string) => apiFetch<{ message: string }>(`/api/v1/alerts/${id}/dismiss`, { method: 'PATCH' }),

  // Utils
  spectrogramUrl: (analysisId: string) => `${API_BASE}/api/v1/analysis/${analysisId}/spectrogram`,
  audioUrl: (filename: string) => `${API_BASE}/uploads/${filename}`,
};
