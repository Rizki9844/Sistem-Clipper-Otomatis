"""
Video Editor Service — Core Clipping Engine 🎬
=================================================
The most critical service: integrates AI-generated timestamps
with FFmpeg for precise video trimming, smart cropping,
face tracking, and transitions.

This is the answer to:
"Fungsi Python yang menggabungkan output timestamp dari LLM
dengan eksekusi pemotongan video menggunakan FFmpeg."
"""

import os
import subprocess
import tempfile
import json
from typing import Optional
from dataclasses import dataclass

from app.config import settings
from app.services.ai_analyzer import HighlightSegment
from app.utils.ffmpeg_utils import (
    probe_video,
    build_trim_command,
    build_crop_command,
    build_transition_command,
    seconds_to_ffmpeg_time,
)


@dataclass
class ClipResult:
    """Result of a video clip operation."""
    output_path: str
    start_time: float
    end_time: float
    duration: float
    width: int
    height: int
    file_size_bytes: int
    success: bool
    error: Optional[str] = None


class VideoEditor:
    """
    Enterprise video editing engine.
    Combines AI segment timestamps with FFmpeg processing.
    """

    def __init__(self):
        self.ffmpeg = settings.FFMPEG_PATH
        self.ffprobe = settings.FFPROBE_PATH

    # ===========================================================
    # CORE FUNCTION: LLM Timestamps → FFmpeg Clip Generation
    # ===========================================================

    async def generate_clips_from_highlights(
        self,
        source_video_path: str,
        highlights: list[HighlightSegment],
        output_dir: str,
        crop_to_portrait: bool = True,
        add_transitions: bool = True,
        normalize_audio: bool = True,
    ) -> list[ClipResult]:
        """
        🔥 CORE FUNCTION: Take AI-generated highlight timestamps
        and produce trimmed, cropped, polished video clips.

        Args:
            source_video_path: Path to the source video file
            highlights: List of HighlightSegment from AI analyzer
            output_dir: Directory to save generated clips
            crop_to_portrait: Convert to 9:16 portrait mode
            add_transitions: Add fade in/out transitions
            normalize_audio: Normalize audio levels

        Returns:
            List of ClipResult with paths and metadata
        """
        os.makedirs(output_dir, exist_ok=True)

        # Get source video info
        video_info = probe_video(source_video_path, self.ffprobe)

        results = []
        for idx, segment in enumerate(highlights):
            try:
                clip_result = await self._process_single_clip(
                    source_path=source_video_path,
                    segment=segment,
                    clip_index=idx,
                    output_dir=output_dir,
                    video_info=video_info,
                    crop_to_portrait=crop_to_portrait,
                    add_transitions=add_transitions,
                    normalize_audio=normalize_audio,
                )
                results.append(clip_result)
            except Exception as e:
                results.append(ClipResult(
                    output_path="",
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    duration=segment.end_time - segment.start_time,
                    width=0,
                    height=0,
                    file_size_bytes=0,
                    success=False,
                    error=str(e),
                ))

        return results

    async def _process_single_clip(
        self,
        source_path: str,
        segment: HighlightSegment,
        clip_index: int,
        output_dir: str,
        video_info: dict,
        crop_to_portrait: bool,
        add_transitions: bool,
        normalize_audio: bool,
    ) -> ClipResult:
        """Process a single clip through the editing pipeline."""

        duration = segment.end_time - segment.start_time
        src_width = video_info.get("width", 1920)
        src_height = video_info.get("height", 1080)

        output_filename = f"clip_{clip_index:03d}_score{segment.score:.1f}.mp4"
        output_path = os.path.join(output_dir, output_filename)

        # ---- Build FFmpeg filter chain ----
        filters = []

        # Step 1: Trim
        # Using -ss (input seeking) for keyframe-accurate seeking
        # and -t for duration — this is the FASTEST method
        input_args = [
            "-ss", seconds_to_ffmpeg_time(segment.start_time),
            "-i", source_path,
            "-t", seconds_to_ffmpeg_time(duration),
        ]

        # Step 2: Smart Crop to Portrait (9:16)
        if crop_to_portrait and src_width > src_height:
            # Landscape → Portrait: crop center with face-tracking offset
            target_w, target_h = 1080, 1920
            crop_filter = self._build_smart_crop_filter(
                src_width, src_height, target_w, target_h
            )
            filters.append(crop_filter)
            out_width, out_height = target_w, target_h
        else:
            out_width, out_height = src_width, src_height

        # Step 3: Scale to standard output resolution
        filters.append(f"scale={out_width}:{out_height}:flags=lanczos")

        # Step 4: Fade transitions
        if add_transitions:
            fade_duration = 0.5  # seconds
            filters.append(f"fade=t=in:st=0:d={fade_duration}")
            filters.append(f"fade=t=out:st={duration - fade_duration}:d={fade_duration}")

        # Step 5: Audio normalization
        audio_filters = []
        if normalize_audio:
            audio_filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")

        # ---- Build final FFmpeg command ----
        cmd = [self.ffmpeg, "-y"]  # -y = overwrite output
        cmd.extend(input_args)

        # Video filters
        if filters:
            cmd.extend(["-vf", ",".join(filters)])

        # Audio filters
        if audio_filters:
            cmd.extend(["-af", ",".join(audio_filters)])

        # Output encoding settings
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",  # Enable streaming
            "-pix_fmt", "yuv420p",
            output_path,
        ])

        # ---- Execute FFmpeg ----
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout per clip
        )

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg error: {result.stderr[-500:]}")

        # Get output file size
        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0

        return ClipResult(
            output_path=output_path,
            start_time=segment.start_time,
            end_time=segment.end_time,
            duration=duration,
            width=out_width,
            height=out_height,
            file_size_bytes=file_size,
            success=True,
        )

    def _build_smart_crop_filter(
        self,
        src_w: int,
        src_h: int,
        target_w: int,
        target_h: int,
    ) -> str:
        """
        Build FFmpeg crop filter for landscape → portrait conversion.
        Centers the crop; future: integrate face detection for smart offset.

        For 1920x1080 → 1080x1920:
        - We need 9:16 aspect ratio from 16:9 source
        - Crop width = src_height * (9/16) = 1080 * 0.5625 = 607.5
        - Then scale up to target resolution
        """
        target_aspect = target_w / target_h  # 9/16 = 0.5625

        # Calculate crop dimensions maintaining target aspect ratio
        if src_w / src_h > target_aspect:
            # Source is wider — crop width
            crop_h = src_h
            crop_w = int(src_h * target_aspect)
        else:
            # Source is taller — crop height
            crop_w = src_w
            crop_h = int(src_w / target_aspect)

        # Center crop (default — face tracking can offset this)
        x_offset = (src_w - crop_w) // 2
        y_offset = (src_h - crop_h) // 2

        return f"crop={crop_w}:{crop_h}:{x_offset}:{y_offset}"

    # ===========================================================
    # ADVANCED: Face-Tracked Smart Cropping
    # ===========================================================

    async def generate_clips_with_face_tracking(
        self,
        source_video_path: str,
        highlights: list[HighlightSegment],
        output_dir: str,
    ) -> list[ClipResult]:
        """
        Generate clips with MediaPipe face tracking
        for intelligent portrait cropping.
        """
        from app.services.face_tracker import FaceTracker
        tracker = FaceTracker()

        results = []
        for idx, segment in enumerate(highlights):
            # Detect face positions in the segment
            face_positions = await tracker.detect_faces_in_segment(
                source_video_path,
                segment.start_time,
                segment.end_time,
            )

            # Generate clip with face-centered cropping
            clip = await self._process_clip_with_faces(
                source_path=source_video_path,
                segment=segment,
                clip_index=idx,
                output_dir=output_dir,
                face_positions=face_positions,
            )
            results.append(clip)

        return results

    async def _process_clip_with_faces(
        self,
        source_path: str,
        segment: HighlightSegment,
        clip_index: int,
        output_dir: str,
        face_positions: list[dict],
    ) -> ClipResult:
        """Process clip with face-position-aware cropping."""
        video_info = probe_video(source_path, self.ffprobe)
        src_w = video_info.get("width", 1920)
        src_h = video_info.get("height", 1080)
        duration = segment.end_time - segment.start_time

        output_filename = f"clip_{clip_index:03d}_facetrack.mp4"
        output_path = os.path.join(output_dir, output_filename)

        # Calculate average face position for crop offset
        if face_positions:
            avg_x = sum(fp["center_x"] for fp in face_positions) / len(face_positions)
            crop_w = int(src_h * (9 / 16))
            x_offset = int(avg_x * src_w - crop_w / 2)
            x_offset = max(0, min(x_offset, src_w - crop_w))
            crop_filter = f"crop={crop_w}:{src_h}:{x_offset}:0"
        else:
            crop_w = int(src_h * (9 / 16))
            x_offset = (src_w - crop_w) // 2
            crop_filter = f"crop={crop_w}:{src_h}:{x_offset}:0"

        cmd = [
            self.ffmpeg, "-y",
            "-ss", seconds_to_ffmpeg_time(segment.start_time),
            "-i", source_path,
            "-t", seconds_to_ffmpeg_time(duration),
            "-vf", f"{crop_filter},scale=1080:1920:flags=lanczos,"
                   f"fade=t=in:st=0:d=0.5,fade=t=out:st={duration - 0.5}:d=0.5",
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg error: {result.stderr[-500:]}")

        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0

        return ClipResult(
            output_path=output_path,
            start_time=segment.start_time,
            end_time=segment.end_time,
            duration=duration,
            width=1080,
            height=1920,
            file_size_bytes=file_size,
            success=True,
        )
