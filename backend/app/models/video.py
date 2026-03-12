"""
Video Document Model (Beanie ODM)
===================================
Stores metadata for uploaded/downloaded source videos.
Supports both file upload and URL-based ingestion.
"""

from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import Field


class Video(Document):
    """Source video — either uploaded or downloaded from URL."""

    filename: str = ""
    original_filename: str = ""
    file_size_bytes: int = 0
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    codec: Optional[str] = None
    format: Optional[str] = None

    # Azure Blob Storage reference
    blob_url: str = ""
    blob_container: str = ""
    blob_name: str = ""

    # Source info (for URL-based ingestion)
    source_type: str = "upload"  # "upload" or "url"
    source_url: Optional[str] = None
    source_platform: Optional[str] = None  # youtube, tiktok, instagram, etc.
    thumbnail_url: Optional[str] = None
    source_metadata: dict = Field(default_factory=dict)  # uploader, description, etc.

    # Processing metadata
    status: str = Field(default="pending")
    # Status flow:
    #   URL:    pending → downloading → downloaded → transcribing → transcribed → processing → completed
    #   Upload: uploaded → transcribing → transcribed → processing → completed
    language: Optional[str] = None
    tags: list[str] = Field(default_factory=list)

    # User info (for multi-tenant)
    user_id: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "videos"
        indexes = [
            "status",
            "source_type",
            "source_platform",
            "user_id",
            "created_at",
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "original_filename": "podcast_episode_42.mp4",
                "source_type": "url",
                "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "source_platform": "youtube",
                "status": "pending",
            }
        }
