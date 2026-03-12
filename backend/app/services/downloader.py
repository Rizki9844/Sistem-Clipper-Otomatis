"""
Video Downloader Service
===========================
Downloads videos from URLs (YouTube, TikTok, direct links)
using yt-dlp. Supports progress tracking.

The user pastes a link → we download → store in Azure → process.
"""

import os
import re
import json
import tempfile
import subprocess
from typing import Optional
from dataclasses import dataclass, field
from urllib.parse import urlparse

from app.config import settings
from app.logging_config import get_logger
from app.exceptions import (
    VideoDownloadError,
    UnsupportedURLError,
    VideoTooLargeError,
    VideoTooLongError,
)

logger = get_logger("downloader")


@dataclass
class VideoMetadata:
    """Metadata extracted from a video URL before downloading."""
    title: str = ""
    duration_seconds: float = 0.0
    uploader: str = ""
    upload_date: str = ""
    description: str = ""
    thumbnail_url: str = ""
    original_url: str = ""
    extractor: str = ""  # youtube, tiktok, etc.
    format_id: str = ""
    resolution: str = ""
    filesize_approx: int = 0
    fps: float = 0.0
    width: int = 0
    height: int = 0


@dataclass
class DownloadResult:
    """Result of a video download operation."""
    local_path: str
    filename: str
    file_size_bytes: int
    metadata: VideoMetadata
    success: bool
    error: Optional[str] = None


# Supported URL patterns
SUPPORTED_PLATFORMS = {
    "youtube": [
        r"(youtube\.com|youtu\.be)",
    ],
    "tiktok": [
        r"(tiktok\.com|vm\.tiktok\.com)",
    ],
    "instagram": [
        r"(instagram\.com|instagr\.am)",
    ],
    "twitter": [
        r"(twitter\.com|x\.com)",
    ],
    "facebook": [
        r"(facebook\.com|fb\.watch)",
    ],
    "vimeo": [
        r"vimeo\.com",
    ],
    "twitch": [
        r"(twitch\.tv|clips\.twitch\.tv)",
    ],
    "direct": [
        r"\.(mp4|mov|avi|webm|mkv)(\?|$)",
    ],
}


class VideoDownloader:
    """
    Downloads video from any supported URL using yt-dlp.
    Extracts metadata, validates constraints, and returns local file.
    """

    def __init__(self):
        self.yt_dlp_path = "yt-dlp"
        self.max_duration = settings.MAX_VIDEO_DURATION_MINUTES * 60
        self.max_size = settings.max_video_size_bytes

    def identify_platform(self, url: str) -> str:
        """Identify which platform a URL belongs to."""
        for platform, patterns in SUPPORTED_PLATFORMS.items():
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return platform
        return "unknown"

    async def extract_metadata(self, url: str) -> VideoMetadata:
        """
        Extract video metadata WITHOUT downloading the video.
        Fast pre-check before committing to a full download.
        """
        logger.info("Extracting metadata", url=url)

        platform = self.identify_platform(url)
        if platform == "unknown":
            # Still try — yt-dlp supports 1000+ sites
            logger.warning("Unknown platform, attempting anyway", url=url)

        cmd = [
            self.yt_dlp_path,
            "--dump-json",
            "--no-download",
            "--no-playlist",
            "--no-warnings",
            url,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode != 0:
                raise VideoDownloadError(
                    f"Failed to extract metadata: {result.stderr[:300]}",
                    details={"url": url, "stderr": result.stderr[:500]},
                )

            data = json.loads(result.stdout)

            metadata = VideoMetadata(
                title=data.get("title", "Untitled"),
                duration_seconds=float(data.get("duration", 0) or 0),
                uploader=data.get("uploader", "Unknown"),
                upload_date=data.get("upload_date", ""),
                description=(data.get("description", "") or "")[:500],
                thumbnail_url=data.get("thumbnail", ""),
                original_url=url,
                extractor=data.get("extractor", platform),
                resolution=data.get("resolution", ""),
                filesize_approx=int(data.get("filesize_approx", 0) or 0),
                fps=float(data.get("fps", 0) or 0),
                width=int(data.get("width", 0) or 0),
                height=int(data.get("height", 0) or 0),
            )

            logger.info(
                "Metadata extracted",
                title=metadata.title,
                duration=metadata.duration_seconds,
                platform=metadata.extractor,
            )

            return metadata

        except json.JSONDecodeError as e:
            raise VideoDownloadError(
                f"Invalid metadata response from yt-dlp",
                details={"url": url, "error": str(e)},
            )
        except subprocess.TimeoutExpired:
            raise VideoDownloadError(
                "Metadata extraction timed out (60s)",
                details={"url": url},
            )

    def validate_video(self, metadata: VideoMetadata) -> None:
        """
        Validate video constraints before downloading.
        Raises appropriate exceptions if constraints are violated.
        """
        # Check duration
        if metadata.duration_seconds > self.max_duration:
            raise VideoTooLongError(
                f"Video is {metadata.duration_seconds / 60:.1f} minutes. "
                f"Maximum: {settings.MAX_VIDEO_DURATION_MINUTES} minutes.",
                details={
                    "duration": metadata.duration_seconds,
                    "max_duration": self.max_duration,
                },
            )

        # Check estimated file size (if available)
        if metadata.filesize_approx > 0 and metadata.filesize_approx > self.max_size:
            raise VideoTooLargeError(
                f"Estimated file size: {metadata.filesize_approx / 1024 / 1024:.0f}MB. "
                f"Maximum: {settings.MAX_VIDEO_SIZE_MB}MB.",
                details={
                    "filesize_approx": metadata.filesize_approx,
                    "max_size": self.max_size,
                },
            )

    async def download(
        self,
        url: str,
        output_dir: Optional[str] = None,
        preferred_quality: str = "best[height<=1080]",
        progress_callback=None,
    ) -> DownloadResult:
        """
        Download a video from URL.

        Args:
            url: Video URL (YouTube, TikTok, direct link, etc.)
            output_dir: Directory to save the video (default: temp dir)
            preferred_quality: yt-dlp format selector
            progress_callback: Async callback(percent: float, speed: str)

        Returns:
            DownloadResult with local file path and metadata
        """
        logger.info("Starting download", url=url)

        # Step 1: Extract metadata
        metadata = await self.extract_metadata(url)

        # Step 2: Validate constraints
        self.validate_video(metadata)

        # Step 3: Prepare output
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="clipper_dl_")

        # Sanitize filename
        safe_title = re.sub(r'[^\w\s\-.]', '', metadata.title)[:80].strip() or "video"
        output_template = os.path.join(output_dir, f"{safe_title}.%(ext)s")

        # Step 4: Download with yt-dlp
        cmd = [
            self.yt_dlp_path,
            "--no-playlist",
            "--no-warnings",
            "--newline",  # Progress on new lines
            "-f", preferred_quality + "/best",  # Fallback to best if quality not available
            "--merge-output-format", "mp4",
            "-o", output_template,
            # Embed metadata
            "--embed-thumbnail",
            "--embed-metadata",
            # Limit rate to be a good citizen
            "--limit-rate", "50M",
            # SponsorBlock: skip sponsors for cleaner transcription
            "--sponsorblock-remove", "sponsor,selfpromo,interaction,intro,outro",
            url,
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            output_lines = []
            for line in iter(process.stdout.readline, ""):
                line = line.strip()
                if line:
                    output_lines.append(line)

                    # Parse download progress
                    if progress_callback and "%" in line:
                        try:
                            match = re.search(r'(\d+\.?\d*)%', line)
                            if match:
                                percent = float(match.group(1))
                                speed_match = re.search(r'at\s+(\S+)', line)
                                speed = speed_match.group(1) if speed_match else ""
                                import asyncio
                                try:
                                    loop = asyncio.get_event_loop()
                                    if loop.is_running():
                                        loop.create_task(progress_callback(percent, speed))
                                except RuntimeError:
                                    pass
                        except (ValueError, AttributeError):
                            pass

            process.wait(timeout=1800)  # 30 minute timeout

            if process.returncode != 0:
                error_text = "\n".join(output_lines[-5:])
                raise VideoDownloadError(
                    f"Download failed (exit code {process.returncode})",
                    details={"url": url, "output": error_text},
                )

        except subprocess.TimeoutExpired:
            process.kill()
            raise VideoDownloadError(
                "Download timed out after 30 minutes",
                details={"url": url},
            )

        # Step 5: Find the downloaded file
        downloaded_file = self._find_downloaded_file(output_dir, safe_title)

        if not downloaded_file:
            raise VideoDownloadError(
                "Download completed but output file not found",
                details={"url": url, "output_dir": output_dir},
            )

        file_size = os.path.getsize(downloaded_file)

        # Post-download size check
        if file_size > self.max_size:
            os.remove(downloaded_file)
            raise VideoTooLargeError(
                f"Downloaded file is {file_size / 1024 / 1024:.0f}MB. "
                f"Maximum: {settings.MAX_VIDEO_SIZE_MB}MB.",
            )

        logger.info(
            "Download complete",
            title=metadata.title,
            size_mb=round(file_size / 1024 / 1024, 1),
            path=downloaded_file,
        )

        return DownloadResult(
            local_path=downloaded_file,
            filename=os.path.basename(downloaded_file),
            file_size_bytes=file_size,
            metadata=metadata,
            success=True,
        )

    def _find_downloaded_file(self, directory: str, expected_name: str) -> Optional[str]:
        """Find the downloaded video file in the output directory."""
        video_extensions = {".mp4", ".mkv", ".webm", ".mov", ".avi"}

        # First try exact match
        for ext in video_extensions:
            candidate = os.path.join(directory, f"{expected_name}{ext}")
            if os.path.exists(candidate):
                return candidate

        # Fuzzy match: find any video file in the directory
        for filename in os.listdir(directory):
            _, ext = os.path.splitext(filename)
            if ext.lower() in video_extensions:
                return os.path.join(directory, filename)

        return None

    async def download_thumbnail(
        self,
        thumbnail_url: str,
        output_path: str,
    ) -> Optional[str]:
        """Download video thumbnail for preview."""
        if not thumbnail_url:
            return None

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(thumbnail_url, timeout=30)
                response.raise_for_status()
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return output_path
        except Exception as e:
            logger.warning("Thumbnail download failed", error=str(e))
            return None
