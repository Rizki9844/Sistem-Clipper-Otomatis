"""
Whisper Transcription Service
================================
Speech-to-text using OpenAI Whisper with
word-level timestamp extraction.
"""

import os
import tempfile
from typing import Optional

import whisper
import numpy as np

from app.config import settings
from app.models.transcript import Transcript, TranscriptSegment, WordTimestamp


class TranscriptionService:
    """
    Transcribe video/audio using OpenAI Whisper.
    Extracts word-level timestamps for precise caption rendering.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.WHISPER_MODEL
        self._model = None

    @property
    def model(self):
        """Lazy-load the Whisper model (it's large)."""
        if self._model is None:
            print(f"🔄 Loading Whisper model: {self.model_name}...")
            self._model = whisper.load_model(self.model_name)
            print(f"✅ Whisper model loaded: {self.model_name}")
        return self._model

    async def transcribe_video(
        self,
        video_path: str,
        language: Optional[str] = None,
    ) -> Transcript:
        """
        Transcribe a video file and return structured transcript
        with word-level timestamps.

        Args:
            video_path: Path to the video/audio file
            language: Language code (e.g., 'en', 'id') or None for auto-detect

        Returns:
            Transcript document with segments and word timestamps
        """
        import time
        start_time = time.time()

        # Run Whisper
        result = self.model.transcribe(
            video_path,
            language=language,
            task="transcribe",
            word_timestamps=True,  # Critical for word-level timing
            verbose=False,
        )

        processing_time = time.time() - start_time

        # Extract segments with word-level timestamps
        segments = []
        for idx, seg in enumerate(result.get("segments", [])):
            words = []
            for word_data in seg.get("words", []):
                words.append(WordTimestamp(
                    word=word_data["word"].strip(),
                    start=round(word_data["start"], 3),
                    end=round(word_data["end"], 3),
                    confidence=round(word_data.get("probability", 1.0), 3),
                ))

            segments.append(TranscriptSegment(
                id=idx,
                text=seg["text"].strip(),
                start=round(seg["start"], 3),
                end=round(seg["end"], 3),
                words=words,
            ))

        # Build transcript document
        transcript = Transcript(
            video_id="",  # Set by caller
            language=language or "auto",
            detected_language=result.get("language", "unknown"),
            confidence=self._calculate_average_confidence(segments),
            full_text=result.get("text", "").strip(),
            segments=segments,
            model_used=f"whisper-{self.model_name}",
            processing_time_seconds=round(processing_time, 2),
        )

        return transcript

    def _calculate_average_confidence(self, segments: list[TranscriptSegment]) -> float:
        """Calculate average word confidence across all segments."""
        all_confidences = []
        for seg in segments:
            for word in seg.words:
                all_confidences.append(word.confidence)

        if not all_confidences:
            return 0.0
        return round(sum(all_confidences) / len(all_confidences), 3)
