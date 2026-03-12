"""
Custom Exception Hierarchy
=============================
Structured exceptions for the entire pipeline.
Each exception carries context for Sentry and logging.
"""


class ClipperBaseError(Exception):
    """Base exception for the Auto Clipper system."""

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


# ---- Ingestion Errors ----

class VideoDownloadError(ClipperBaseError):
    """Failed to download video from URL."""
    pass


class UnsupportedURLError(ClipperBaseError):
    """The provided URL is not supported."""
    pass


class VideoTooLargeError(ClipperBaseError):
    """Video exceeds maximum allowed file size."""
    pass


class VideoTooLongError(ClipperBaseError):
    """Video exceeds maximum allowed duration."""
    pass


class InvalidVideoFormatError(ClipperBaseError):
    """Video format is not supported."""
    pass


# ---- Transcription Errors ----

class TranscriptionError(ClipperBaseError):
    """Whisper transcription failed."""
    pass


class LanguageDetectionError(ClipperBaseError):
    """Could not detect the language of the audio."""
    pass


class EmptyTranscriptError(ClipperBaseError):
    """Transcription produced no text (silent video or music-only)."""
    pass


# ---- AI Analysis Errors ----

class AIAnalysisError(ClipperBaseError):
    """LLM analysis failed."""
    pass


class NoHighlightsFoundError(ClipperBaseError):
    """AI could not find any highlight-worthy segments."""
    pass


class LLMRateLimitError(ClipperBaseError):
    """LLM API rate limit exceeded."""
    pass


class InvalidLLMResponseError(ClipperBaseError):
    """LLM returned an unparseable response."""
    pass


# ---- Video Editing Errors ----

class FFmpegError(ClipperBaseError):
    """FFmpeg command failed."""

    def __init__(self, message: str, command: list[str] | None = None,
                 stderr: str = "", return_code: int = -1):
        super().__init__(message, details={
            "command": " ".join(command) if command else "",
            "stderr_tail": stderr[-500:] if stderr else "",
            "return_code": return_code,
        })
        self.command = command
        self.stderr = stderr
        self.return_code = return_code


class CropError(ClipperBaseError):
    """Smart cropping operation failed."""
    pass


class FaceDetectionError(ClipperBaseError):
    """Face detection/tracking failed."""
    pass


# ---- Caption Errors ----

class CaptionRenderError(ClipperBaseError):
    """Caption/subtitle rendering failed."""
    pass


class StyleNotFoundError(ClipperBaseError):
    """Requested caption style template not found."""
    pass


# ---- Storage Errors ----

class StorageUploadError(ClipperBaseError):
    """Failed to upload file to Azure Blob Storage."""
    pass


class StorageDownloadError(ClipperBaseError):
    """Failed to download file from Azure Blob Storage."""
    pass


class BlobNotFoundError(ClipperBaseError):
    """Requested blob does not exist in storage."""
    pass


# ---- Notification Errors ----

class NotificationError(ClipperBaseError):
    """Notification delivery failed (non-fatal)."""
    pass


# ---- Pipeline Errors ----

class PipelineError(ClipperBaseError):
    """Pipeline orchestration error."""

    def __init__(self, message: str, step: str = "", job_id: str = "",
                 details: dict | None = None):
        super().__init__(message, details={
            **(details or {}),
            "step": step,
            "job_id": job_id,
        })
        self.step = step
        self.job_id = job_id


class JobCancelledError(ClipperBaseError):
    """Job was cancelled by user or system."""
    pass


class MaxRetriesExceededError(ClipperBaseError):
    """Task exceeded maximum retry attempts."""
    pass
