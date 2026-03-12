"""
Application Schemas (Pydantic)
================================
Request/Response schemas for the API.
Separated from models for clean architecture.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ---- Job Schemas ----

class JobResponse(BaseModel):
    """Detailed job status response."""
    id: str
    video_id: str
    status: str
    current_step: str
    overall_progress: float
    steps: list[dict]
    config: dict
    total_clips_found: int
    total_clips_rendered: int
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time: Optional[str] = None

    @classmethod
    def from_job(cls, job) -> "JobResponse":
        processing_time = None
        if job.started_at and job.completed_at:
            delta = job.completed_at - job.started_at
            minutes = int(delta.total_seconds() / 60)
            seconds = int(delta.total_seconds() % 60)
            processing_time = f"{minutes}m {seconds}s"
        elif job.started_at:
            delta = datetime.utcnow() - job.started_at
            minutes = int(delta.total_seconds() / 60)
            processing_time = f"{minutes}m (running)"

        return cls(
            id=str(job.id),
            video_id=job.video_id,
            status=job.status,
            current_step=job.current_step,
            overall_progress=job.overall_progress,
            steps=job.steps,
            config=job.config,
            total_clips_found=job.total_clips_found,
            total_clips_rendered=job.total_clips_rendered,
            error_message=job.error_message,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            processing_time=processing_time,
        )


# ---- Clip Schemas ----

class ClipResponse(BaseModel):
    """Clip details response."""
    id: str
    video_id: str
    job_id: str
    start_time: float
    end_time: float
    duration: float
    highlight_score: float
    hook_text: str
    category: str
    status: str
    blob_url: Optional[str] = None
    has_captions: bool = False
    has_face_tracking: bool = False
    review_status: str = "pending"
    created_at: datetime

    @classmethod
    def from_clip(cls, clip) -> "ClipResponse":
        return cls(
            id=str(clip.id),
            video_id=clip.video_id,
            job_id=clip.job_id,
            start_time=clip.start_time,
            end_time=clip.end_time,
            duration=clip.duration,
            highlight_score=clip.highlight_score,
            hook_text=clip.hook_text,
            category=clip.category,
            status=clip.status,
            blob_url=clip.blob_url,
            has_captions=getattr(clip, "has_captions", False),
            has_face_tracking=getattr(clip, "has_face_tracking", False),
            review_status=getattr(clip, "review_status", "pending"),
            created_at=clip.created_at,
        )


# ---- Dashboard Schemas ----

class DashboardStats(BaseModel):
    """Aggregate stats for the dashboard."""
    total_videos: int
    total_jobs: int
    total_clips: int
    jobs_processing: int
    jobs_completed: int
    jobs_failed: int
    avg_processing_time_minutes: float
    clips_approved: int
    clips_rejected: int
