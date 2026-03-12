"""
Job Document Model (Beanie ODM)
=================================
Tracks processing pipeline jobs with status, progress,
and per-job configuration.
"""

from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import Field

from app.services.pipeline import PipelineOrchestrator


class Job(Document):
    """Processing job tracking the full 5-stage pipeline."""

    video_id: str
    status: str = Field(default="queued")
    # Status: queued → processing → completed → failed → cancelled
    priority: int = Field(default=5, ge=1, le=10)

    # Pipeline progress
    current_step: str = "queued"
    overall_progress: float = 0.0  # 0-100

    # Step tracking (initialized by PipelineOrchestrator)
    steps: list[dict] = Field(default_factory=PipelineOrchestrator.create_job_steps)

    # Results
    total_clips_found: int = 0
    total_clips_rendered: int = 0
    clip_ids: list[str] = Field(default_factory=list)

    # Per-job configuration
    config: dict = Field(default_factory=lambda: {
        "quality_preset": "balanced",
        "crop_to_portrait": True,
        "face_tracking": True,
        "add_captions": True,
        "caption_style_id": None,
        "add_transitions": True,
        "normalize_audio": True,
        "max_clips": 10,
        "min_highlight_score": 5.0,
        "target_aspect_ratio": "9:16",
        "language": None,
    })

    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    # Notification preferences
    notify_whatsapp: bool = False
    notify_telegram: bool = True
    whatsapp_number: Optional[str] = None
    notification_sent: bool = False

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Settings:
        name = "jobs"
        indexes = [
            "video_id",
            "status",
            "priority",
            "created_at",
        ]
