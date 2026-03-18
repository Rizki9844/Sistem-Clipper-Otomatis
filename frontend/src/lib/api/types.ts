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

// ---- Quota ----
export interface QuotaInfo {
  plan_tier: "free" | "starter" | "pro" | "business" | "enterprise";
  used: number;
  limit: number;
  unlimited: boolean;
  remaining: number | null;
  reset_date: string;
}

// ---- Billing / Subscription ----
export interface SubscriptionStatus {
  plan_tier: "free" | "starter" | "pro" | "business" | "enterprise";
  subscription_status: "active" | "trialing" | "past_due" | "canceled" | "inactive";
  monthly_quota: number;
  used_quota: number;
  trial_end_date: string | null;
  features: PlanFeatures;
  is_trial: boolean;
}

export interface PlanFeatures {
  display_name: string;
  price_monthly: number;
  monthly_quota: number;
  max_video_duration_minutes: number;
  max_clips_per_video: number;
  max_quality: string;
  watermark: boolean;
  publish_platforms: string[];
  queue_priority: number;
  custom_captions: boolean;
  analytics: boolean | string;
  api_access: boolean;
  team_seats: number;
}

export interface PricingPlan {
  tier: string;
  badge: string | null;
  cta: string;
  features: string[];
  not_included: string[];
}

// ---- Social Publishing ----
export interface SocialAccount {
  id: string;
  platform: "tiktok" | "instagram" | "youtube";
  username: string;
  avatar: string | null;
  connected_at: string;
  token_expires_at: string | null;
}

export interface PublishJobEntry {
  id: string;
  clip_id: string;
  platform: "tiktok" | "instagram" | "youtube";
  status: "pending" | "processing" | "published" | "failed" | "scheduled";
  platform_post_url: string | null;
  scheduled_at: string | null;
  published_at: string | null;
  error_message: string | null;
  created_at: string;
}

export interface PublishRequest {
  platform: string;
  social_account_id: string;
  caption: string;
  hashtags: string[];
  scheduled_at?: string | null;
}

// ---- Admin ----
export interface AdminUserDetail {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_admin: boolean;
  plan_tier: "free" | "pro";
  monthly_quota: number;
  used_quota: number;
  created_at: string;
  last_login: string | null;
  total_videos: number;
  total_jobs: number;
  total_clips: number;
}

export interface AdminStats {
  users: {
    total: number;
    active: number;
    free_plan: number;
    pro_plan: number;
  };
  videos: { total: number };
  jobs: {
    total: number;
    processing: number;
    completed: number;
    failed: number;
    queued: number;
  };
  clips: { total: number };
}

export interface AdminJobEntry {
  id: string;
  video_id: string;
  status: string;
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
  user_email: string;
}

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
