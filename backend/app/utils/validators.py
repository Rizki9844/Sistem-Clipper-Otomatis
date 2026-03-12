"""
Input Validators
==================
Validate video files, configurations, and user input.
"""

import os
from typing import Optional

from app.config import settings


ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm", ".mkv", ".m4v"}
ALLOWED_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/webm",
    "video/x-matroska",
}


def validate_video_file(
    filename: str,
    file_size: int,
    content_type: Optional[str] = None,
) -> tuple[bool, str]:
    """
    Validate a video file before processing.

    Returns:
        (is_valid, error_message)
    """
    # Check extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        return False, f"Unsupported file extension: {ext}. Allowed: {ALLOWED_VIDEO_EXTENSIONS}"

    # Check MIME type
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        return False, f"Unsupported MIME type: {content_type}"

    # Check file size
    max_bytes = settings.max_video_size_bytes
    if file_size > max_bytes:
        return False, f"File too large: {file_size / 1024 / 1024:.1f}MB (max: {settings.MAX_VIDEO_SIZE_MB}MB)"

    if file_size == 0:
        return False, "File is empty"

    return True, ""


def validate_clip_config(
    start_time: float,
    end_time: float,
    video_duration: float,
) -> tuple[bool, str]:
    """Validate clip timing configuration."""
    if start_time < 0:
        return False, "Start time cannot be negative"
    if end_time <= start_time:
        return False, "End time must be after start time"
    if end_time > video_duration:
        return False, f"End time ({end_time}s) exceeds video duration ({video_duration}s)"

    duration = end_time - start_time
    if duration < settings.CLIP_MIN_DURATION_SECONDS:
        return False, f"Clip too short: {duration:.1f}s (min: {settings.CLIP_MIN_DURATION_SECONDS}s)"
    if duration > settings.CLIP_MAX_DURATION_SECONDS:
        return False, f"Clip too long: {duration:.1f}s (max: {settings.CLIP_MAX_DURATION_SECONDS}s)"

    return True, ""
