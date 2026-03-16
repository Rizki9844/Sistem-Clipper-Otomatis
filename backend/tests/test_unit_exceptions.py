"""
Unit Tests: Custom Exceptions
================================
Tests for the ClipperBaseError hierarchy and the to_dict() serialization
used by the global exception handler in main.py.
"""

import pytest

from app.exceptions import (
    ClipperBaseError,
    VideoDownloadError,
    VideoTooLargeError,
    VideoTooLongError,
    TranscriptionError,
    EmptyTranscriptError,
    AIAnalysisError,
    NoHighlightsFoundError,
    LLMRateLimitError,
    InvalidLLMResponseError,
    FFmpegError,
    CropError,
    StorageUploadError,
    StorageDownloadError,
    BlobNotFoundError,
    NotificationError,
    PipelineError,
    JobCancelledError,
    MaxRetriesExceededError,
)


# ------------------------------------------------------------------ Base exception

class TestClipperBaseError:
    def test_inherits_from_exception(self):
        err = ClipperBaseError("test message")
        assert isinstance(err, Exception)

    def test_message_stored(self):
        err = ClipperBaseError("something went wrong")
        assert err.message == "something went wrong"

    def test_details_default_to_empty_dict(self):
        err = ClipperBaseError("oops")
        assert err.details == {}

    def test_details_accepted(self):
        err = ClipperBaseError("oops", details={"key": "value"})
        assert err.details == {"key": "value"}

    def test_to_dict_structure(self):
        err = ClipperBaseError("test message", details={"foo": "bar"})
        d = err.to_dict()
        assert d["error"] == "ClipperBaseError"
        assert d["message"] == "test message"
        assert d["details"] == {"foo": "bar"}

    def test_to_dict_error_uses_class_name(self):
        err = VideoDownloadError("download failed")
        d = err.to_dict()
        assert d["error"] == "VideoDownloadError"

    def test_str_representation_is_message(self):
        err = ClipperBaseError("hello error")
        assert str(err) == "hello error"


# ------------------------------------------------------------------ Subclass hierarchy

_SIMPLE_SUBCLASSES = [
    VideoDownloadError,
    VideoTooLargeError,
    VideoTooLongError,
    TranscriptionError,
    EmptyTranscriptError,
    AIAnalysisError,
    NoHighlightsFoundError,
    LLMRateLimitError,
    InvalidLLMResponseError,
    CropError,
    StorageUploadError,
    StorageDownloadError,
    BlobNotFoundError,
    NotificationError,
    JobCancelledError,
    MaxRetriesExceededError,
]


@pytest.mark.parametrize("exc_class", _SIMPLE_SUBCLASSES)
def test_subclass_inherits_base(exc_class):
    err = exc_class("error message")
    assert isinstance(err, ClipperBaseError)
    assert err.message == "error message"
    d = err.to_dict()
    assert d["error"] == exc_class.__name__


# ------------------------------------------------------------------ Specialised exceptions

class TestFFmpegError:
    def test_stores_command_and_stderr(self):
        err = FFmpegError(
            message="FFmpeg failed",
            command=["ffmpeg", "-i", "input.mp4"],
            stderr="No such file",
            return_code=1,
        )
        assert err.return_code == 1
        assert err.command == ["ffmpeg", "-i", "input.mp4"]
        assert "No such file" in err.stderr

    def test_to_dict_includes_ffmpeg_details(self):
        err = FFmpegError(
            message="FFmpeg failed",
            command=["ffmpeg", "-i", "in.mp4"],
            stderr="error output here",
            return_code=2,
        )
        d = err.to_dict()
        assert d["error"] == "FFmpegError"
        assert d["details"]["return_code"] == 2
        assert "ffmpeg" in d["details"]["command"]

    def test_long_stderr_is_truncated_to_500_chars(self):
        long_stderr = "x" * 1000
        err = FFmpegError("fail", stderr=long_stderr)
        assert len(err.details["stderr_tail"]) <= 500

    def test_no_command_still_works(self):
        err = FFmpegError("fail")
        d = err.to_dict()
        assert d["details"]["command"] == ""


class TestPipelineError:
    def test_stores_step_and_job_id(self):
        err = PipelineError("pipeline broke", step="transcribe", job_id="abc123")
        assert err.step == "transcribe"
        assert err.job_id == "abc123"

    def test_to_dict_includes_step_info(self):
        err = PipelineError("pipeline broke", step="analyze", job_id="job999")
        d = err.to_dict()
        assert d["details"]["step"] == "analyze"
        assert d["details"]["job_id"] == "job999"

    def test_extra_details_merged(self):
        err = PipelineError("fail", step="edit", details={"clip_id": "c1"})
        d = err.to_dict()
        assert d["details"]["clip_id"] == "c1"
        assert d["details"]["step"] == "edit"
