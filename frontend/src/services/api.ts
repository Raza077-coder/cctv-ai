import type {
  AlertItem, AnalyticsSummary, Camera, CameraStats, DetectionItem,
  EventItem, Health, PlateItem,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* keep statusText */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>('/health'),

  // Cameras
  listCameras: () => request<Camera[]>('/cameras'),
  getCamera: (id: number) => request<Camera>(`/cameras/${id}`),
  createCamera: (data: Partial<Camera>) =>
    request<Camera>('/cameras', { method: 'POST', body: JSON.stringify(data) }),
  updateCamera: (id: number, data: Partial<Camera>) =>
    request<Camera>(`/cameras/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteCamera: (id: number) => request<void>(`/cameras/${id}`, { method: 'DELETE' }),
  startDetection: (cameraId: number, processFps?: number) =>
    request<{ status: string; camera_id: number; fps: number }>('/cameras/detection/start', {
      method: 'POST',
      body: JSON.stringify({ camera_id: cameraId, process_fps: processFps }),
    }),
  stopDetection: (cameraId: number) =>
    request<{ status: string; camera_id: number }>('/cameras/detection/stop', {
      method: 'POST',
      body: JSON.stringify({ camera_id: cameraId }),
    }),

  // Events / Alerts
  listEvents: (params?: Record<string, string | number>) => {
    const qs = new URLSearchParams(
      Object.entries(params || {}).map(([k, v]) => [k, String(v)]),
    ).toString();
    return request<{ total: number; items: EventItem[] }>(`/events${qs ? `?${qs}` : ''}`);
  },
  listAlerts: (params?: Record<string, string | number>) => {
    const qs = new URLSearchParams(
      Object.entries(params || {}).map(([k, v]) => [k, String(v)]),
    ).toString();
    return request<{ total: number; items: AlertItem[] }>(`/alerts${qs ? `?${qs}` : ''}`);
  },
  ackAlert: (id: number, status: string) =>
    request<AlertItem>(`/alerts/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }),

  // Analytics
  summary: () => request<AnalyticsSummary>('/analytics/summary'),
  detections: (params?: Record<string, string | number>) => {
    const qs = new URLSearchParams(
      Object.entries(params || {}).map(([k, v]) => [k, String(v)]),
    ).toString();
    return request<{ total: number; items: DetectionItem[] }>(`/analytics/detections${qs ? `?${qs}` : ''}`);
  },
  plates: (params?: Record<string, string | number>) => {
    const qs = new URLSearchParams(
      Object.entries(params || {}).map(([k, v]) => [k, String(v)]),
    ).toString();
    return request<{ total: number; items: PlateItem[] }>(`/analytics/plates${qs ? `?${qs}` : ''}`);
  },
  classBreakdown: () => request<{ items: { class: string; count: number }[] }>('/analytics/classes'),
  cameraStats: (id: number) => request<CameraStats>(`/analytics/camera/${id}/stats`),
};
