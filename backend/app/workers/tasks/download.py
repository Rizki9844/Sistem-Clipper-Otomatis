"""
Download Worker Task
=======================
Celery task: Download video from URL using yt-dlp,
extract metadata, upload to Azure Blob Storage.

This is the NEW first step in the pipeline (before transcription).
"""

import os
import shutil
import tempfile
import asyncio
from datetime import datetime

from app.workers.celery_app import celery_app
from app.logging_config import get_logger

logger = get_logger("task.download")


@celery_app.task(
    bind=True,
    name="app.workers.tasks.download.download_video",
    max_retries=2,
    default_retry_delay=120,
    soft_time_limit=1500,
    time_limit=1800,
)
def download_video(self, video_id: str, job_id: str, source_url: str):
    """
    Task 0/4 in pipeline: Download video from URL.

    Pipeline: [Download] → Transcribe → Analyze → Edit → Render

    Steps:
        1. Download video from URL via yt-dlp
        2. Extract video metadata (duration, resolution, etc.)
        3. Upload to Azure Blob Storage
        4. Update Video & Job records
        5. Enqueue transcription task
    """
    async def _run():
        from app.database import init_database
        from app.models.video import Video
        from app.models.job import Job
        from app.services.downloader import VideoDownloader
        from app.services.storage import AzureBlobStorage
        from app.services.pipeline import PipelineOrchestrator
        from app.utils.ffmpeg_utils import probe_video
        from app.exceptions import VideoDownloadError

        await init_database()

        video = await Video.get(video_id)
        job = await Job.get(job_id)

        if not video or not job:
            raise ValueError(f"Video {video_id} or Job {job_id} not found")

        try:
            # Start download step
            job.status = "processing"
            job.started_at = datetime.utcnow()
            PipelineOrchestrator.update_step(job, "download", "running", 5)
            await job.save()

            # Check cancellation
            await PipelineOrchestrator.check_cancellation(job)

            # Step 1: Download video
            downloader = VideoDownloader()

            async def progress_cb(percent, speed):
                PipelineOrchestrator.update_step(
                    job, "download", "running", min(percent * 0.7, 70),
                    metadata={"speed": speed}
                )
                await job.save()

            result = await downloader.download(
                url=source_url,
                progress_callback=progress_cb,
            )

            PipelineOrchestrator.update_step(job, "download", "running", 75,
                                             metadata={"title": result.metadata.title})
            await job.save()

            logger.info(
                "Video downloaded",
                video_id=video_id,
                title=result.metadata.title,
                size_mb=round(result.file_size_bytes / 1024 / 1024, 1),
            )

            # Step 2: Probe video metadata
            video_info = probe_video(result.local_path)

            # Step 3: Upload to Azure Blob Storage
            storage = AzureBlobStorage()
            blob_name, blob_url = await storage.upload_video(
                content=open(result.local_path, "rb").read(),
                original_filename=result.filename,
                content_type="video/mp4",
            )

            PipelineOrchestrator.update_step(job, "download", "running", 90)
            await job.save()

            # Step 4: Update video record with full metadata
            video.filename = blob_name
            video.original_filename = result.metadata.title or result.filename
            video.file_size_bytes = result.file_size_bytes
            video.duration_seconds = video_info.get("duration") or result.metadata.duration_seconds
            video.width = video_info.get("width") or result.metadata.width
            video.height = video_info.get("height") or result.metadata.height
            video.fps = video_info.get("fps") or result.metadata.fps
            video.codec = video_info.get("codec", "")
            video.format = video_info.get("format_name", "mp4")
            video.blob_url = blob_url
            video.blob_container = "raw-videos"
            video.blob_name = blob_name
            video.source_url = source_url
            video.source_platform = result.metadata.extractor
            video.thumbnail_url = result.metadata.thumbnail_url
            video.source_metadata = {
                "uploader": result.metadata.uploader,
                "upload_date": result.metadata.upload_date,
                "description": result.metadata.description,
            }
            video.status = "downloaded"
            await video.save()

            # Clean up temp file
            try:
                os.remove(result.local_path)
                parent_dir = os.path.dirname(result.local_path)
                if os.path.isdir(parent_dir) and parent_dir.startswith(tempfile.gettempdir()):
                    shutil.rmtree(parent_dir, ignore_errors=True)
            except Exception:
                pass

            PipelineOrchestrator.update_step(
                job, "download", "completed", 100,
                metadata={
                    "title": result.metadata.title,
                    "duration": video.duration_seconds,
                    "platform": result.metadata.extractor,
                }
            )
            await job.save()

            # Enqueue next task: Transcription
            from app.workers.tasks.transcribe import transcribe_video
            transcribe_video.delay(video_id, job_id)

            logger.info(
                "Download complete, transcription enqueued",
                video_id=video_id,
                job_id=job_id,
            )

            return {
                "status": "success",
                "title": result.metadata.title,
                "duration": video.duration_seconds,
                "platform": result.metadata.extractor,
            }

        except Exception as e:
            logger.error("Download failed", video_id=video_id, error=str(e))
            job.status = "failed"
            job.error_message = str(e)
            PipelineOrchestrator.update_step(job, "download", "failed", 0, error=str(e))
            await job.save()

            video.status = "failed"
            await video.save()

            raise self.retry(exc=e)

    asyncio.run(_run())
