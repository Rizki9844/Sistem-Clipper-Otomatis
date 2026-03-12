"""
Video Editing Worker Task
============================
Celery task: Trim, crop, and edit individual clips
using the VideoEditor engine with job-level config.

Pipeline: Download → Transcribe → Analyze → [Edit] → Render
"""

import os
import shutil
import tempfile
import asyncio
from datetime import datetime

from app.workers.celery_app import celery_app
from app.logging_config import get_logger

logger = get_logger("task.edit")


@celery_app.task(
    bind=True,
    name="app.workers.tasks.edit_video.edit_clip",
    max_retries=2,
    default_retry_delay=120,
    soft_time_limit=500,
    time_limit=600,
)
def edit_clip(self, video_id: str, job_id: str, clip_id: str):
    """
    Task 4/5 in pipeline: Edit a single clip.

    Steps:
        1. Download source video from Azure
        2. Optionally detect faces for smart cropping
        3. Trim + crop + transitions + audio normalize via FFmpeg
        4. Upload edited clip to Azure
        5. Enqueue render task (captions)
    """
    async def _run():
        from app.database import init_database
        from app.models.video import Video
        from app.models.job import Job
        from app.models.clip import Clip
        from app.services.storage import AzureBlobStorage
        from app.services.video_editor import VideoEditor
        from app.services.ai_analyzer import HighlightSegment
        from app.services.pipeline import PipelineOrchestrator, JobConfig
        from app.exceptions import FFmpegError

        await init_database()

        video = await Video.get(video_id)
        job = await Job.get(job_id)
        clip = await Clip.get(clip_id)

        if not all([video, job, clip]):
            raise ValueError("Missing video, job, or clip")

        job_config = JobConfig.from_dict(job.config)

        try:
            await PipelineOrchestrator.check_cancellation(job)

            clip.status = "editing"
            await clip.save()
            PipelineOrchestrator.update_step(job, "edit", "running", 20)
            await job.save()

            logger.info(
                "Starting edit",
                clip_id=clip_id,
                start=clip.start_time,
                end=clip.end_time,
                score=clip.highlight_score,
            )

            # Step 1: Download source video
            storage = AzureBlobStorage()
            temp_dir = tempfile.mkdtemp(prefix="clipper_edit_")
            local_video = os.path.join(temp_dir, video.filename or "source.mp4")
            await storage.download_to_file(
                blob_name=video.blob_name,
                local_path=local_video,
                container=video.blob_container,
            )

            # Step 2: Build highlight segment
            segment = HighlightSegment(
                start_time=clip.start_time,
                end_time=clip.end_time,
                score=clip.highlight_score,
                hook_text=clip.hook_text,
                category=clip.category,
                reasoning=clip.ai_reasoning,
            )

            # Step 3: Edit with face tracking or standard cropping
            editor = VideoEditor()
            output_dir = os.path.join(temp_dir, "output")

            if job_config.face_tracking and job_config.crop_to_portrait:
                results = await editor.generate_clips_with_face_tracking(
                    source_video_path=local_video,
                    highlights=[segment],
                    output_dir=output_dir,
                )
                clip.has_face_tracking = True
            else:
                results = await editor.generate_clips_from_highlights(
                    source_video_path=local_video,
                    highlights=[segment],
                    output_dir=output_dir,
                    crop_to_portrait=job_config.crop_to_portrait,
                    add_transitions=job_config.add_transitions,
                    normalize_audio=job_config.normalize_audio,
                )

            if not results or not results[0].success:
                error_msg = results[0].error if results else "No result"
                raise FFmpegError(f"Edit failed: {error_msg}")

            result = results[0]

            # Step 4: Upload edited clip
            blob_name = f"clip_{clip_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4"
            blob_url = await storage.upload_from_file(
                local_path=result.output_path,
                blob_name=blob_name,
                content_type="video/mp4",
            )

            clip.blob_url = blob_url
            clip.blob_name = blob_name
            clip.width = result.width
            clip.height = result.height
            clip.status = "edited"
            await clip.save()

            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)

            logger.info(
                "Edit complete",
                clip_id=clip_id,
                size_mb=round(result.file_size_bytes / 1024 / 1024, 1),
                resolution=f"{result.width}x{result.height}",
            )

            # Update job progress
            total = len(job.clip_ids)
            edited = await Clip.find(
                Clip.job_id == job_id,
                Clip.status.is_in(["edited", "rendering", "completed"])
            ).count()
            progress = (edited / total * 100) if total > 0 else 100
            PipelineOrchestrator.update_step(job, "edit", "running", progress)
            await job.save()

            # Step 5: Enqueue caption rendering
            if job_config.add_captions:
                from app.workers.tasks.render import render_clip
                render_clip.delay(video_id, job_id, clip_id)
            else:
                # Skip captions — mark as completed
                clip.status = "completed"
                clip.rendered_at = datetime.utcnow()
                await clip.save()
                await _check_job_completion(job_id, video, job)

            return {"status": "success", "clip_id": clip_id}

        except Exception as e:
            logger.error("Edit failed", clip_id=clip_id, error=str(e))
            clip.status = "failed"
            await clip.save()

            # Check if all clips failed
            total = len(job.clip_ids) if job.clip_ids else 1
            failed = await Clip.find(Clip.job_id == job_id, Clip.status == "failed").count()
            if failed >= total:
                job.status = "failed"
                job.error_message = f"All {total} clips failed to edit"
                PipelineOrchestrator.update_step(job, "edit", "failed", 0, error=str(e))
                await job.save()
            elif self.request.retries < self.max_retries:
                raise self.retry(exc=e)

    asyncio.run(_run())


async def _check_job_completion(job_id: str, video, job):
    """Check if all clips are done and finalize job."""
    from app.models.clip import Clip
    from app.services.notifier import Notifier
    from app.services.pipeline import PipelineOrchestrator

    total = await Clip.find(Clip.job_id == job_id).count()
    completed = await Clip.find(Clip.job_id == job_id, Clip.status == "completed").count()

    if completed >= total:
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.total_clips_rendered = completed
        PipelineOrchestrator.update_step(job, "edit", "completed", 100)
        PipelineOrchestrator.update_step(job, "render", "skipped", 100)
        await job.save()

        notifier = Notifier()
        await notifier.notify_job_completed(
            job_id=job_id,
            video_name=video.original_filename,
            clips_count=completed,
            notify_telegram=job.notify_telegram,
            notify_whatsapp=job.notify_whatsapp,
            whatsapp_number=job.whatsapp_number,
        )
