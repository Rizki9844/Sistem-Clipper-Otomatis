"""
PublishJob Document Model (Beanie ODM)
========================================
Tracking pekerjaan publish clip ke platform sosial media.
Status flow: pending → processing → published | failed
"""

from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import Field
from bson import PydanticObjectId


class PublishJob(Document):
    """A queued/completed publish job for a clip to a social platform."""

    user_id: PydanticObjectId
    clip_id: PydanticObjectId
    social_account_id: PydanticObjectId
    platform: str                           # "tiktok" | "instagram" | "youtube"

    # Content
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)

    # Scheduling
    scheduled_at: Optional[datetime] = None  # None = publish sekarang
    published_at: Optional[datetime] = None

    # Status
    status: str = "pending"                  # "pending" | "processing" | "published" | "failed" | "scheduled"
    platform_post_id: Optional[str] = None   # ID post dari platform setelah publish
    platform_post_url: Optional[str] = None  # URL post setelah publish
    error_message: Optional[str] = None
    retry_count: int = 0

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "publish_jobs"
        indexes = [
            "user_id",
            "clip_id",
            "status",
            "scheduled_at",
        ]
