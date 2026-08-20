export interface Camera {
  id: number;
  name: string;
  source_type: 'webcam' | 'file' | 'rtsp';
  source_url: string;
  location: string | null;
  enabled: boolean;
  detection_settings: Record<string, unknown>;
  alert_settings: Record<string, unknown>;
  status: string;
  last_seen: string | null;
  created_at: string;
}

export interface EventItem {
  id: number;
  camera_id: number | null;
  event_type: string;
  message: string;
  confidence: number | null;
  severity: string;
  metadata: Record<string, unknown>;
  snapshot_path: string | null;
  created_at: string;
}

export interface AlertItem {
  id: number;
  camera_id: number | null;
  alert_type: string;
  title: string;
  message: string;
  severity: string;
  status: string;
  snapshot_path: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface DetectionItem {
  id: number;
  camera_id: number | null;
  object_class: string;
  confidence: number;
  track_id: number | null;
  bbox: { x1: number; y1: number; x2: number; y2: number };
  frame_number: number | null;
  created_at: string;
}

export interface PlateItem {
  id: number;
  plate_number: string;
  normalized_plate: string;
  confidence: number;
  camera_id: number | null;
  snapshot_path: string | null;
  created_at: string;
}

export interface CameraStats {
  camera_id: number;
  camera_name: string;
  events_24h: number;
  alerts_24h: number;
  people_count: number;
  vehicle_count: number;
  detections_24h: number;
}

export interface AnalyticsSummary {
  total_cameras: number;
  active_cameras: number;
  events_24h: number;
  alerts_active: number;
  people_detected_24h: number;
  vehicles_detected_24h: number;
  plates_detected_24h: number;
  per_camera: CameraStats[];
}

export interface Health {
  status: string;
  app: string;
  version: string;
  database: string;
  redis: string;
  models_loaded: string[];
  features: Record<string, boolean>;
}

export interface LiveFrameStats {
  camera_id: number;
  people: number;
  vehicles: number;
  fps: number;
  motion: boolean;
  crowd_level: string;
  alerts: { type: string; message: string; severity: string }[];
}
