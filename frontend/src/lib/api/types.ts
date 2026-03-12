// ============================================================
// AutoClipperPro — API Type Definitions
// Mirrors backend Pydantic schemas exactly
// ============================================================

// ---- Video ----
export interface Video {
  id: string;
  filename: string;
  original_filename: string;
  file_size_bytes: number;
  duration_seconds: number | null;
  source_type: "upload" | "url";
  source_url: string | null;
  source_platform: string | null;
  thumbnail_url: string | null;
  status: string;
  created_at: string;
}

// ---- Job ----
export interface JobStep {
  name: string;
  display: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  progress: number;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  metadata: Record<string, unknown>;
}

export interface JobConfig {
  quality_preset: string;
  crop_to_portrait: boolean;
  face_tracking: boolean;
  add_captions: boolean;
  caption_style_id: string | null;
  add_transitions: boolean;
  normalize_audio: boolean;
  max_clips: number;
  min_highlight_score: number;
  target_aspect_ratio: string;
  language: string | null;
}

export interface Job {
  id: string;
  video_id: string;
  status: "queued" | "processing" | "completed" | "failed" | "cancelled";
  current_step: string;
  overall_progress: number;
  steps: JobStep[];
  config: JobConfig;
  total_clips_found: number;
  total_clips_rendered: number;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  processing_time: string | null;
}

// ---- Clip ----
export interface Clip {
  id: string;
  video_id: string;
  job_id: string;
  start_time: number;
  end_time: number;
  duration: number;
  highlight_score: number;
  hook_text: string;
  category: string;
  status: string;
  blob_url: string | null;
  has_captions: boolean;
  has_face_tracking: boolean;
  review_status: "pending" | "approved" | "rejected";
  suggested_title?: string;
  ai_reasoning?: string;
  hashtags?: string[];
  review_notes?: string | null;
  created_at: string;
}

// ---- Dashboard Stats ----
export interface DashboardStats {
  total_videos: number;
  total_jobs: number;
  total_clips: number;
  jobs_processing: number;
  jobs_completed: number;
  jobs_failed: number;
  avg_processing_time_minutes: number;
  clips_approved: number;
  clips_rejected: number;
}

// ---- Request/Response ----
export interface URLSubmitRequest {
  url: string;
  quality: string;
  crop_to_portrait: boolean;
  face_tracking: boolean;
  add_captions: boolean;
  caption_style_id?: string | null;
  max_clips: number;
  min_highlight_score: number;
  target_aspect_ratio: string;
  language?: string | null;
  notify_whatsapp: boolean;
  notify_telegram: boolean;
  whatsapp_number?: string | null;
}

export interface SubmitResponse {
  video_id: string;
  job_id: string;
  message: string;
  estimated_time: string | null;
}

// ---- WebSocket Events ----
export interface WSProgressEvent {
  type: "initial" | "progress" | "heartbeat" | "pong";
  job_id?: string;
  status?: string;
  step?: string;
  progress?: number;
  steps?: JobStep[];
  metadata?: Record<string, unknown>;
}

// ---- Filters ----
export interface VideoFilters {
  status?: string;
  source_type?: string;
  platform?: string;
  limit?: number;
  skip?: number;
}

export interface JobFilters {
  status?: string;
  video_id?: string;
  limit?: number;
  skip?: number;
}

export interface ClipFilters {
  video_id?: string;
  job_id?: string;
  status?: string;
  review_status?: string;
  min_score?: number;
  sort_by?: "score" | "time" | "status";
  limit?: number;
  skip?: number;
}
