"""
Transcription Worker Task
============================
Celery task: Transcribe video using Whisper STT,
extract word-level timestamps, save to MongoDB.

Pipeline: Download → [Transcribe] → Analyze → Edit → Render
"""

import os
import tempfile
import asyncio
from datetime import datetime

from app.workers.celery_app import celery_app
from app.logging_config import get_logger

logger = get_logger("task.transcribe")


@celery_app.task(
    bind=True,
    name="app.workers.tasks.transcribe.transcribe_video",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=800,
    time_limit=900,
)
def transcribe_video(self, video_id: str, job_id: str):
    """
    Task 2/5 in pipeline: Transcribe with Whisper.

    Steps:
        1. Download video from Azure Blob to local temp
        2. Extract video metadata via ffprobe
        3. Run Whisper with word-level timestamps
        4. Save transcript to MongoDB
        5. Enqueue AI analysis
    """
    async def _run():
        from app.database import init_database
        from app.models.video import Video
        from app.models.job import Job
        from app.services.storage import AzureBlobStorage
        from app.services.transcription import TranscriptionService
        from app.services.pipeline import PipelineOrchestrator, JobConfig
        from app.utils.ffmpeg_utils import probe_video
        from app.exceptions import TranscriptionError, EmptyTranscriptError
        import shutil

        await init_database()

        video = await Video.get(video_id)
        job = await Job.get(job_id)

        if not video or not job:
            raise ValueError(f"Video {video_id} or Job {job_id} not found")

        job_config = JobConfig.from_dict(job.config)

        try:
            await PipelineOrchestrator.check_cancellation(job)

            # Update status
            job.status = "processing"
            if not job.started_at:
                job.started_at = datetime.utcnow()
            PipelineOrchestrator.update_step(job, "transcribe", "running", 5)
            await job.save()

            logger.info("Starting transcription", video_id=video_id, job_id=job_id)

            # Step 1: Download video to temp file
            storage = AzureBlobStorage()
            temp_dir = tempfile.mkdtemp(prefix="clipper_trans_")
            local_path = os.path.join(temp_dir, video.filename or "video.mp4")

            await storage.download_to_file(
                blob_name=video.blob_name,
                local_path=local_path,
                container=video.blob_container,
            )
            PipelineOrchestrator.update_step(job, "transcribe", "running", 15)
            await job.save()

            # Step 2: Extract video metadata (if not already done)
            if not video.duration_seconds:
                video_info = probe_video(local_path)
                video.duration_seconds = video_info.get("duration")
                video.width = video_info.get("width")
                video.height = video_info.get("height")
                video.fps = video_info.get("fps")
                video.codec = video_info.get("codec")
                await video.save()

            PipelineOrchestrator.update_step(job, "transcribe", "running", 20)
            await job.save()

            # Step 3: Transcribe with Whisper
            transcription_service = TranscriptionService()
            transcript = await transcription_service.transcribe_video(
                video_path=local_path,
                language=job_config.language,
            )

            # Validate transcript
            if not transcript.full_text or len(transcript.full_text.strip()) < 10:
                raise EmptyTranscriptError(
                    "Transcription produced no usable text. The video may be silent or music-only.",
                    details={"video_id": video_id},
                )

            transcript.video_id = video_id
            await transcript.insert()

            logger.info(
                "Transcription complete",
                video_id=video_id,
                language=transcript.detected_language,
                segments=len(transcript.segments),
                words=sum(len(s.words) for s in transcript.segments),
                duration=transcript.processing_time_seconds,
            )

            # Step 4: Update records
            video.language = transcript.detected_language
            video.status = "transcribed"
            await video.save()

            PipelineOrchestrator.update_step(
                job, "transcribe", "completed", 100,
                metadata={
                    "language": transcript.detected_language,
                    "segments": len(transcript.segments),
                    "confidence": transcript.confidence,
                }
            )
            await job.save()

            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)

            # Step 5: Enqueue AI analysis
            from app.workers.tasks.analyze import analyze_highlights
            analyze_highlights.delay(video_id, job_id, str(transcript.id))

            return {
                "status": "success",
                "transcript_id": str(transcript.id),
                "language": transcript.detected_language,
                "segments": len(transcript.segments),
            }

        except Exception as e:
            logger.error("Transcription failed", video_id=video_id, error=str(e))
            job.error_message = str(e)
            PipelineOrchestrator.update_step(job, "transcribe", "failed", 0, error=str(e))
            await job.save()

            # Only mark job as failed if retries exhausted
            if self.request.retries >= self.max_retries:
                job.status = "failed"
                await job.save()
            else:
                raise self.retry(exc=e)

    asyncio.run(_run())
