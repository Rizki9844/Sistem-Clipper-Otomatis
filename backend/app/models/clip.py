"""
Clip Document Model (Beanie ODM)
===================================
Stores generated clip metadata including AI analysis,
storage references, and user review state.
"""

from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import Field


class Clip(Document):
    """A generated video clip from the editing pipeline."""

    video_id: str
    job_id: str

    # Timing (from AI analysis)
    start_time: float
    end_time: float
    duration: float

    # AI Analysis
    highlight_score: float = 0.0
    hook_text: str = ""
    category: str = ""  # hook, punchline, emotional, etc.
    ai_reasoning: str = ""
    suggested_title: str = ""
    hashtags: list[str] = Field(default_factory=list)

    # Video properties
    orientation: str = "portrait"  # portrait | landscape | square
    width: Optional[int] = None
    height: Optional[int] = None
    has_captions: bool = False
    has_face_tracking: bool = False
    caption_style_id: Optional[str] = None

    # Azure Blob Storage
    blob_url: Optional[str] = None
    blob_name: Optional[str] = None

    # Processing status
    status: str = Field(default="pending")
    # Status: pending → editing → edited → rendering → completed → failed

    # Human review
    review_status: str = Field(default="pending")
    # Review: pending → approved | rejected
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    rendered_at: Optional[datetime] = None

    class Settings:
        name = "clips"
        indexes = [
            "video_id",
            "job_id",
            "status",
            "review_status",
            "highlight_score",
        ]
