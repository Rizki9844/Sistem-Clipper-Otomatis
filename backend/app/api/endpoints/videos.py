"""
Videos API Endpoints
======================
Upload files OR submit URLs for processing.
The primary entry point for the video clipper system.
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from pydantic import BaseModel, Field, HttpUrl
from starlette.requests import Request

from app.config import settings
from app.models.video import Video
from app.models.job import Job
from app.services.storage import AzureBlobStorage
from app.services.pipeline import PipelineOrchestrator, JobConfig
from app.api.deps import get_current_user, check_quota
from app.api.rate_limit import limiter
from app.models.user import User
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("api.videos")


# ---- Response Models ----

class VideoResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_size_bytes: int
    duration_seconds: Optional[float] = None
    source_type: str
    source_url: Optional[str] = None
    source_platform: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: str
    created_at: datetime


class SubmitResponse(BaseModel):
    video_id: str
    job_id: str
    message: str
    estimated_time: Optional[str] = None


# ---- Request Models ----

class URLSubmitRequest(BaseModel):
    """Submit a video URL for processing."""
    url: str = Field(..., description="Video URL (YouTube, TikTok, Instagram, direct link, etc.)")

    # Processing options
    quality: str = Field(default="balanced", description="Quality preset: fast, balanced, high")
    crop_to_portrait: bool = Field(default=True, description="Convert to 9:16 portrait")
    face_tracking: bool = Field(default=True, description="Use face detection for smart cropping")
    add_captions: bool = Field(default=True, description="Add Hormozi-style captions")
    caption_style_id: Optional[str] = Field(default=None, description="Custom caption style ID")
    max_clips: int = Field(default=10, ge=1, le=50, description="Maximum clips to generate")
    min_highlight_score: float = Field(default=5.0, ge=0, le=10, description="Minimum AI score threshold")
    target_aspect_ratio: str = Field(default="9:16", description="Output aspect ratio: 9:16, 16:9, 1:1")
    language: Optional[str] = Field(default=None, description="Force language (e.g., 'en', 'id') or auto-detect")

    # Notifications
    notify_whatsapp: bool = Field(default=False, description="Send WhatsApp notification")
    notify_telegram: bool = Field(default=True, description="Send Telegram notification")
    whatsapp_number: Optional[str] = Field(default=None, description="WhatsApp number (with country code)")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "quality": "balanced",
                "crop_to_portrait": True,
                "add_captions": True,
                "max_clips": 5,
                "notify_telegram": True,
            }
        }


# ============================================================
# 🔥 PRIMARY ENDPOINT: Submit URL for Processing
# ============================================================

@router.post("/from-url", response_model=SubmitResponse)
@limiter.limit(settings.RATE_LIMIT_SUBMIT)
async def submit_url(
    request: Request,
    body: URLSubmitRequest,
    current_user: User = Depends(check_quota),
):
    """
    🔗 Submit a video URL for full AI processing.

    Supported platforms: YouTube, TikTok, Instagram, Twitter/X,
    Facebook, Vimeo, Twitch, and 1000+ more via yt-dlp.

    Pipeline: Download → Transcribe → AI Analyze → Edit → Render → Notify

    The process runs asynchronously. Track progress via:
    - GET /api/v1/jobs/{job_id} (polling)
    - WS /api/v1/ws/progress (real-time)
    """
    logger.info("URL submitted", url=body.url)

    # Quick URL validation
    from app.services.downloader import VideoDownloader
    downloader = VideoDownloader()
    platform = downloader.identify_platform(body.url)

    # Pre-flight: extract metadata (fast, no download)
    try:
        metadata = await downloader.extract_metadata(body.url)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not access video at URL: {str(e)}"
        )

    # Validate duration based on user's plan
    from app.services.plan_config import get_plan
    user_plan = get_plan(current_user.plan_tier)
    max_duration_plan = user_plan["max_video_duration_minutes"]
    max_clips_plan = user_plan["max_clips_per_video"]

    # Check plan duration limit (0 = unlimited)
    if max_duration_plan > 0 and metadata.duration_seconds > max_duration_plan * 60:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "DURATION_LIMIT",
                "message": (
                    f"Your {current_user.plan_tier} plan supports videos up to {max_duration_plan} minutes. "
                    f"This video is {metadata.duration_seconds / 60:.0f} minutes. Upgrade to process longer videos."
                ),
                "current_plan": current_user.plan_tier,
                "limit_minutes": max_duration_plan,
            },
        )
    # Fallback global limit
    elif metadata.duration_seconds > settings.MAX_VIDEO_DURATION_MINUTES * 60:
        raise HTTPException(
            status_code=400,
            detail=f"Video is {metadata.duration_seconds / 60:.0f} minutes. "
                   f"Maximum: {settings.MAX_VIDEO_DURATION_MINUTES} minutes."
        )

    # Enforce clips per video limit from plan (0 = unlimited)
    effective_max_clips = body.max_clips
    if max_clips_plan > 0:
        effective_max_clips = min(body.max_clips, max_clips_plan)

    # Create Video record (metadata-only, no blob yet)
    video = Video(
        original_filename=metadata.title or "Untitled",
        source_type="url",
        source_url=body.url,
        source_platform=platform,
        thumbnail_url=metadata.thumbnail_url,
        duration_seconds=metadata.duration_seconds,
        width=metadata.width,
        height=metadata.height,
        fps=metadata.fps,
        source_metadata={
            "uploader": metadata.uploader,
            "upload_date": metadata.upload_date,
            "description": metadata.description[:500] if metadata.description else "",
        },
        status="pending",
        user_id=str(current_user.id),
    )
    await video.insert()

    # Build job config from request
    job_config = JobConfig(
        quality_preset=body.quality,
        crop_to_portrait=body.crop_to_portrait,
        face_tracking=body.face_tracking,
        add_captions=body.add_captions,
        caption_style_id=body.caption_style_id,
        max_clips=effective_max_clips,
        min_highlight_score=body.min_highlight_score,
        target_aspect_ratio=body.target_aspect_ratio,
        notify_whatsapp=body.notify_whatsapp,
        notify_telegram=body.notify_telegram,
        whatsapp_number=body.whatsapp_number,
        language=body.language,
    )

    # Create Job with full config
    job = Job(
        video_id=str(video.id),
        user_id=str(current_user.id),
        config=job_config.to_dict(),
        notify_whatsapp=body.notify_whatsapp,
        notify_telegram=body.notify_telegram,
        whatsapp_number=body.whatsapp_number,
    )
    await job.insert()

    # Increment quota counter
    await current_user.set({User.used_quota: current_user.used_quota + 1})

    # Enqueue with priority based on plan (0=highest, 9=lowest)
    task_priority = user_plan["queue_priority"]
    from app.workers.tasks.download import download_video
    download_video.apply_async(
        args=[str(video.id), str(job.id), body.url],
        priority=task_priority,
    )

    # Estimate processing time
    est_minutes = max(5, int(metadata.duration_seconds / 60 * 2))
    estimated_time = f"~{est_minutes} minutes"

    logger.info(
        "Job created",
        video_id=str(video.id),
        job_id=str(job.id),
        platform=platform,
        title=metadata.title,
        estimated_time=estimated_time,
    )

    return SubmitResponse(
        video_id=str(video.id),
        job_id=str(job.id),
        message=f"🎬 Video '{metadata.title}' queued for processing. "
                f"You'll be notified when clips are ready!",
        estimated_time=estimated_time,
    )


# ============================================================
# File Upload Endpoint (Legacy/Alternative)
# ============================================================

@router.post("/upload", response_model=SubmitResponse)
@limiter.limit("5/minute")
async def upload_video(
    request: Request,
    file: UploadFile = File(...),
    quality: str = Query("balanced", description="Quality preset"),
    crop_to_portrait: bool = Query(True),
    add_captions: bool = Query(True),
    max_clips: int = Query(10, ge=1, le=50),
    notify_telegram: bool = Query(True),
    notify_whatsapp: bool = Query(False),
    current_user: User = Depends(get_current_user),
):
    """
    📤 Upload a video file for processing.
    For URL-based ingestion (recommended), use POST /from-url instead.
    """
    storage = AzureBlobStorage()

    # Validate file type
    allowed_types = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/webm", "video/x-matroska"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    content = await file.read()
    file_size = len(content)

    if file_size > settings.max_video_size_bytes:
        raise HTTPException(status_code=413, detail=f"File too large. Max: {settings.MAX_VIDEO_SIZE_MB}MB")

    # Upload to Azure
    blob_name, blob_url = await storage.upload_video(
        content=content,
        original_filename=file.filename,
        content_type=file.content_type,
    )

    # Create Video record
    video = Video(
        filename=blob_name,
        original_filename=file.filename,
        file_size_bytes=file_size,
        blob_url=blob_url,
        blob_container=settings.AZURE_STORAGE_CONTAINER_RAW,
        blob_name=blob_name,
        format=file.content_type,
        source_type="upload",
        status="uploaded",
        user_id=str(current_user.id),
    )
    await video.insert()

    # Create Job with config
    job_config = JobConfig(
        quality_preset=quality,
        crop_to_portrait=crop_to_portrait,
        add_captions=add_captions,
        max_clips=max_clips,
        notify_telegram=notify_telegram,
        notify_whatsapp=notify_whatsapp,
    )

    job = Job(
        video_id=str(video.id),
        user_id=str(current_user.id),
        config=job_config.to_dict(),
        notify_whatsapp=notify_whatsapp,
        notify_telegram=notify_telegram,
    )
    await job.insert()

    # Skip download step, go straight to transcription
    from app.workers.tasks.transcribe import transcribe_video
    transcribe_video.delay(str(video.id), str(job.id))

    return SubmitResponse(
        video_id=str(video.id),
        job_id=str(job.id),
        message="Video uploaded successfully. Processing started.",
    )


# ============================================================
# CRUD Operations
# ============================================================

@router.get("/", response_model=list[VideoResponse])
async def list_videos(
    status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None, description="Filter: upload or url"),
    platform: Optional[str] = Query(None, description="Filter: youtube, tiktok, etc."),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    """List all videos owned by the current user."""
    query = {"user_id": str(current_user.id)}
    if status:
        query["status"] = status
    if source_type:
        query["source_type"] = source_type
    if platform:
        query["source_platform"] = platform

    videos = await Video.find(query).sort("-created_at").skip(skip).limit(limit).to_list()

    return [
        VideoResponse(
            id=str(v.id),
            filename=v.filename,
            original_filename=v.original_filename,
            file_size_bytes=v.file_size_bytes,
            duration_seconds=v.duration_seconds,
            source_type=v.source_type,
            source_url=v.source_url,
            source_platform=v.source_platform,
            thumbnail_url=v.thumbnail_url,
            status=v.status,
            created_at=v.created_at,
        )
        for v in videos
    ]


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get video details by ID."""
    video = await Video.get(video_id)
    if not video or video.user_id != str(current_user.id):
        raise HTTPException(status_code=404, detail="Video not found")

    return VideoResponse(
        id=str(video.id),
        filename=video.filename,
        original_filename=video.original_filename,
        file_size_bytes=video.file_size_bytes,
        duration_seconds=video.duration_seconds,
        source_type=video.source_type,
        source_url=video.source_url,
        source_platform=video.source_platform,
        thumbnail_url=video.thumbnail_url,
        status=video.status,
        created_at=video.created_at,
    )


@router.delete("/{video_id}")
async def delete_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a video and all associated data (jobs, clips, transcripts)."""
    video = await Video.get(video_id)
    if not video or video.user_id != str(current_user.id):
        raise HTTPException(status_code=404, detail="Video not found")

    storage = AzureBlobStorage()

    # Delete from blob storage
    if video.blob_name:
        await storage.delete_blob(video.blob_container, video.blob_name)

    # Delete associated clips from storage
    from app.models.clip import Clip
    clips = await Clip.find(Clip.video_id == video_id).to_list()
    for clip in clips:
        if clip.blob_name:
            await storage.delete_blob("processed-clips", clip.blob_name)
        await clip.delete()

    # Delete transcripts and jobs
    from app.models.transcript import Transcript
    await Transcript.find(Transcript.video_id == video_id).delete()
    await Job.find(Job.video_id == video_id).delete()

    await video.delete()

    logger.info("Video deleted", video_id=video_id)
    return {"message": "Video and all associated data deleted successfully"}
