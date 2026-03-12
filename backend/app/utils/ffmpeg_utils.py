"""
FFmpeg Utility Functions
==========================
Low-level helpers for FFmpeg command building,
video probing, and timestamp handling.
"""

import json
import subprocess
from typing import Optional

from app.config import settings


def probe_video(video_path: str, ffprobe_path: Optional[str] = None) -> dict:
    """
    Extract video metadata using ffprobe.

    Returns:
        dict with keys: width, height, duration, fps, codec, bitrate, etc.
    """
    ffprobe = ffprobe_path or settings.FFPROBE_PATH

    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")

    data = json.loads(result.stdout)

    # Extract video stream info
    video_stream = None
    audio_stream = None
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video" and not video_stream:
            video_stream = stream
        elif stream.get("codec_type") == "audio" and not audio_stream:
            audio_stream = stream

    info = {
        "duration": float(data.get("format", {}).get("duration", 0)),
        "size_bytes": int(data.get("format", {}).get("size", 0)),
        "bitrate": int(data.get("format", {}).get("bit_rate", 0)),
        "format_name": data.get("format", {}).get("format_name", ""),
    }

    if video_stream:
        info.update({
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "fps": _parse_fps(video_stream.get("r_frame_rate", "30/1")),
            "codec": video_stream.get("codec_name", ""),
            "pix_fmt": video_stream.get("pix_fmt", ""),
        })

    if audio_stream:
        info.update({
            "audio_codec": audio_stream.get("codec_name", ""),
            "audio_sample_rate": int(audio_stream.get("sample_rate", 0)),
            "audio_channels": int(audio_stream.get("channels", 0)),
        })

    return info


def _parse_fps(fps_str: str) -> float:
    """Parse FFmpeg fraction FPS string (e.g., '30000/1001') to float."""
    try:
        if "/" in fps_str:
            num, den = fps_str.split("/")
            return round(float(num) / float(den), 3)
        return float(fps_str)
    except (ValueError, ZeroDivisionError):
        return 30.0


def seconds_to_ffmpeg_time(seconds: float) -> str:
    """
    Convert seconds to FFmpeg-compatible timestamp (HH:MM:SS.mmm).

    Examples:
        65.5 → "00:01:05.500"
        3723.123 → "01:02:03.123"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def build_trim_command(
    input_path: str,
    output_path: str,
    start_time: float,
    end_time: float,
    ffmpeg_path: Optional[str] = None,
) -> list[str]:
    """
    Build an FFmpeg command for precise video trimming.
    Uses input seeking (-ss before -i) for fast, keyframe-accurate cuts.
    """
    ffmpeg = ffmpeg_path or settings.FFMPEG_PATH
    duration = end_time - start_time

    return [
        ffmpeg, "-y",
        "-ss", seconds_to_ffmpeg_time(start_time),
        "-i", input_path,
        "-t", seconds_to_ffmpeg_time(duration),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        output_path,
    ]


def build_crop_command(
    input_path: str,
    output_path: str,
    crop_w: int,
    crop_h: int,
    x_offset: int,
    y_offset: int,
    scale_w: int = 1080,
    scale_h: int = 1920,
    ffmpeg_path: Optional[str] = None,
) -> list[str]:
    """Build FFmpeg command for cropping and scaling."""
    ffmpeg = ffmpeg_path or settings.FFMPEG_PATH

    vf = f"crop={crop_w}:{crop_h}:{x_offset}:{y_offset},scale={scale_w}:{scale_h}:flags=lanczos"

    return [
        ffmpeg, "-y",
        "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "copy",
        "-movflags", "+faststart",
        output_path,
    ]


def build_transition_command(
    input_path: str,
    output_path: str,
    fade_in_duration: float = 0.5,
    fade_out_duration: float = 0.5,
    video_duration: Optional[float] = None,
    ffmpeg_path: Optional[str] = None,
) -> list[str]:
    """Build FFmpeg command with fade in/out transitions."""
    ffmpeg = ffmpeg_path or settings.FFMPEG_PATH

    # Need to know video duration for fade out
    if video_duration is None:
        info = probe_video(input_path)
        video_duration = info["duration"]

    fade_out_start = video_duration - fade_out_duration

    vf = (
        f"fade=t=in:st=0:d={fade_in_duration},"
        f"fade=t=out:st={fade_out_start}:d={fade_out_duration}"
    )
    af = (
        f"afade=t=in:st=0:d={fade_in_duration},"
        f"afade=t=out:st={fade_out_start}:d={fade_out_duration}"
    )

    return [
        ffmpeg, "-y",
        "-i", input_path,
        "-vf", vf,
        "-af", af,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ]


def build_subtitle_burn_command(
    input_path: str,
    subtitle_path: str,
    output_path: str,
    ffmpeg_path: Optional[str] = None,
) -> list[str]:
    """Build FFmpeg command to burn ASS subtitles into video."""
    ffmpeg = ffmpeg_path or settings.FFMPEG_PATH

    # Escape Windows path backslashes and colons for FFmpeg filter
    escaped_sub = subtitle_path.replace("\\", "/").replace(":", "\\:")

    return [
        ffmpeg, "-y",
        "-i", input_path,
        "-vf", f"ass='{escaped_sub}'",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "copy",
        "-movflags", "+faststart",
        output_path,
    ]
