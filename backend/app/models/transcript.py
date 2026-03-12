"""
Transcript Document Model (Beanie ODM)
========================================
Stores transcription data with word-level timestamps
from Whisper STT.
"""

from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import BaseModel, Field


class WordTimestamp(BaseModel):
    """Individual word with precise timing."""
    word: str
    start: float  # seconds
    end: float  # seconds
    confidence: float = 1.0


class TranscriptSegment(BaseModel):
    """A segment of continuous speech."""
    id: int
    text: str
    start: float  # seconds
    end: float  # seconds
    words: list[WordTimestamp] = Field(default_factory=list)
    speaker: Optional[str] = None  # For future speaker diarization


class Transcript(Document):
    """Full transcription of a video."""

    video_id: str  # Reference to Video
    language: str = "auto"
    detected_language: Optional[str] = None
    confidence: float = 0.0

    # Full text
    full_text: str = ""

    # Segmented transcript with word-level timestamps
    segments: list[TranscriptSegment] = Field(default_factory=list)

    # Processing info
    model_used: str = "whisper-large-v3"
    processing_time_seconds: Optional[float] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "transcripts"
        indexes = [
            "video_id",
        ]

    def get_text_between(self, start: float, end: float) -> str:
        """Get transcript text between two timestamps."""
        words = []
        for segment in self.segments:
            for word in segment.words:
                if start <= word.start <= end:
                    words.append(word.word)
        return " ".join(words)

    def get_words_between(self, start: float, end: float) -> list[WordTimestamp]:
        """Get word-level timestamps between two time points."""
        result = []
        for segment in self.segments:
            for word in segment.words:
                if start <= word.start <= end:
                    result.append(word)
        return result
