"""
Pipeline Orchestrator Service
=================================
Central coordinator for the 5-stage video processing pipeline.
Manages job lifecycle, step transitions, progress broadcasting,
and error recovery.

Pipeline: Download → Transcribe → Analyze → Edit → Render
"""

import asyncio
from datetime import datetime
from typing import Optional, Callable, Any

from app.config import settings
from app.logging_config import get_logger
from app.exceptions import (
    PipelineError,
    JobCancelledError,
    MaxRetriesExceededError,
)

logger = get_logger("orchestrator")


# Pipeline step definitions with metadata
PIPELINE_STEPS = [
    {
        "name": "download",
        "display": "📥 Downloading Video",
        "weight": 0.10,  # 10% of total progress
        "task": "app.workers.tasks.download.download_video",
        "timeout_seconds": 1800,
        "max_retries": 2,
    },
    {
        "name": "transcribe",
        "display": "🎙️ Transcribing Audio (Whisper)",
        "weight": 0.25,
        "task": "app.workers.tasks.transcribe.transcribe_video",
        "timeout_seconds": 900,
        "max_retries": 3,
    },
    {
        "name": "analyze",
        "display": "🧠 AI Analyzing Highlights",
        "weight": 0.10,
        "task": "app.workers.tasks.analyze.analyze_highlights",
        "timeout_seconds": 300,
        "max_retries": 3,
    },
    {
        "name": "edit",
        "display": "✂️ Editing Video Clips",
        "weight": 0.30,
        "task": "app.workers.tasks.edit_video.edit_clip",
        "timeout_seconds": 600,
        "max_retries": 2,
    },
    {
        "name": "render",
        "display": "🎨 Rendering Captions & Effects",
        "weight": 0.25,
        "task": "app.workers.tasks.render.render_clip",
        "timeout_seconds": 600,
        "max_retries": 2,
    },
]


class QualityPreset:
    """Encoding quality presets for different use cases."""

    PRESETS = {
        "fast": {
            "description": "Fast processing, acceptable quality",
            "crf": 28,
            "preset": "veryfast",
            "audio_bitrate": "128k",
            "max_resolution": 720,
        },
        "balanced": {
            "description": "Good quality, moderate speed",
            "crf": 23,
            "preset": "medium",
            "audio_bitrate": "192k",
            "max_resolution": 1080,
        },
        "high": {
            "description": "Maximum quality, slower processing",
            "crf": 18,
            "preset": "slow",
            "audio_bitrate": "256k",
            "max_resolution": 1920,
        },
    }

    @classmethod
    def get(cls, name: str = "balanced") -> dict:
        return cls.PRESETS.get(name, cls.PRESETS["balanced"])


class JobConfig:
    """
    Per-job configuration that controls pipeline behavior.
    These settings override defaults for a specific job.
    """

    def __init__(
        self,
        quality_preset: str = "balanced",
        crop_to_portrait: bool = True,
        face_tracking: bool = True,
        add_captions: bool = True,
        caption_style_id: Optional[str] = None,
        add_transitions: bool = True,
        normalize_audio: bool = True,
        max_clips: int = 10,
        min_highlight_score: float = 5.0,
        target_aspect_ratio: str = "9:16",  # 9:16, 16:9, 1:1
        notify_whatsapp: bool = False,
        notify_telegram: bool = True,
        whatsapp_number: Optional[str] = None,
        language: Optional[str] = None,  # Force language for Whisper
    ):
        self.quality_preset = quality_preset
        self.crop_to_portrait = crop_to_portrait
        self.face_tracking = face_tracking
        self.add_captions = add_captions
        self.caption_style_id = caption_style_id
        self.add_transitions = add_transitions
        self.normalize_audio = normalize_audio
        self.max_clips = max_clips
        self.min_highlight_score = min_highlight_score
        self.target_aspect_ratio = target_aspect_ratio
        self.notify_whatsapp = notify_whatsapp
        self.notify_telegram = notify_telegram
        self.whatsapp_number = whatsapp_number
        self.language = language

    def to_dict(self) -> dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, data: dict) -> "JobConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__init__.__code__.co_varnames})

    @property
    def encoding(self) -> dict:
        return QualityPreset.get(self.quality_preset)


class PipelineOrchestrator:
    """
    Central coordinator that manages the processing pipeline.

    Responsibilities:
    - Initialize jobs with proper step tracking
    - Update step progress with weighted calculations
    - Handle step transitions and error recovery
    - Broadcast progress via WebSocket
    - Manage job cancellation
    """

    @staticmethod
    def create_job_steps() -> list[dict]:
        """Create initial step tracking structure for a new job."""
        return [
            {
                "name": step["name"],
                "display": step["display"],
                "status": "pending",
                "progress": 0.0,
                "started_at": None,
                "completed_at": None,
                "error": None,
                "metadata": {},
            }
            for step in PIPELINE_STEPS
        ]

    @staticmethod
    def update_step(job, step_name: str, status: str, progress: float,
                    metadata: dict | None = None, error: str | None = None):
        """
        Update a specific step in the job and recalculate overall progress.

        Args:
            job: The Job document
            step_name: Name of the step to update
            status: New status (pending, running, completed, failed, skipped)
            progress: Step progress (0-100)
            metadata: Optional step-specific metadata
            error: Optional error message
        """
        now = datetime.utcnow().isoformat()

        for step in job.steps:
            if step["name"] == step_name:
                step["status"] = status
                step["progress"] = min(100.0, max(0.0, progress))

                if status == "running" and not step.get("started_at"):
                    step["started_at"] = now
                if status in ("completed", "failed", "skipped"):
                    step["completed_at"] = now
                if error:
                    step["error"] = error
                if metadata:
                    step["metadata"] = {**step.get("metadata", {}), **metadata}
                break

        # Recalculate overall progress using weighted sum
        step_weights = {s["name"]: s["weight"] for s in PIPELINE_STEPS}
        total = sum(
            step["progress"] * step_weights.get(step["name"], 0.2)
            for step in job.steps
        )
        job.overall_progress = round(total, 1)
        job.current_step = step_name

        logger.debug(
            "Step updated",
            job_id=str(job.id) if hasattr(job, 'id') else "?",
            step=step_name,
            status=status,
            progress=progress,
            overall=job.overall_progress,
        )

    @staticmethod
    async def broadcast_progress(job_id: str, step: str, progress: float, status: str):
        """Broadcast job progress to WebSocket clients."""
        try:
            from app.api.websocket import broadcast_job_update
            await broadcast_job_update(
                job_id=job_id,
                status=status,
                step=step,
                progress=progress,
            )
        except Exception:
            pass  # WebSocket broadcast is best-effort

    @staticmethod
    async def check_cancellation(job) -> bool:
        """Check if a job has been cancelled by the user."""
        # Refresh from DB
        from app.models.job import Job
        fresh_job = await Job.get(str(job.id))
        if fresh_job and fresh_job.status == "cancelled":
            raise JobCancelledError(
                "Job was cancelled by user",
                details={"job_id": str(job.id)},
            )
        return False

    @staticmethod
    def get_step_config(step_name: str) -> dict:
        """Get configuration for a specific pipeline step."""
        for step in PIPELINE_STEPS:
            if step["name"] == step_name:
                return step
        raise PipelineError(f"Unknown pipeline step: {step_name}", step=step_name)
