"""
Render Worker Task
====================
Celery task: Add dynamic captions and overlays
to edited clips, then finalize and notify.

Pipeline: Download → Transcribe → Analyze → Edit → [Render]
"""

import os
import shutil
import tempfile
import subprocess
import asyncio
from datetime import datetime

from app.workers.celery_app import celery_app
from app.logging_config import get_logger

logger = get_logger("task.render")


@celery_app.task(
    bind=True,
    name="app.workers.tasks.render.render_clip",
    max_retries=2,
    default_retry_delay=60,
    soft_time_limit=500,
    time_limit=600,
)
def render_clip(self, video_id: str, job_id: str, clip_id: str):
    """
    Task 5/5 in pipeline: Caption rendering & finalization.

    Steps:
        1. Get word-level timestamps for this clip's time range
        2. Generate ASS subtitle file (Hormozi-style)
        3. Burn subtitles into video with FFmpeg
        4. Upload final clip to Azure
        5. Check job completion — notify user
    """
    async def _run():
        from app.database import init_database
        from app.models.video import Video
        from app.models.job import Job
        from app.models.clip import Clip
        from app.models.transcript import Transcript
        from app.models.style import CaptionStyle
        from app.services.storage import AzureBlobStorage
        from app.services.caption_renderer import CaptionRenderer
        from app.services.notifier import Notifier
        from app.services.pipeline import PipelineOrchestrator, JobConfig
        from app.utils.ffmpeg_utils import build_subtitle_burn_command

        await init_database()

        video = await Video.get(video_id)
        job = await Job.get(job_id)
        clip = await Clip.get(clip_id)

        if not all([video, job, clip]):
            raise ValueError("Missing video, job, or clip")

        job_config = JobConfig.from_dict(job.config)

        try:
            await PipelineOrchestrator.check_cancellation(job)

            clip.status = "rendering"
            await clip.save()
            PipelineOrchestrator.update_step(job, "render", "running", 20)
            await job.save()

            logger.info("Starting render", clip_id=clip_id, hook=clip.hook_text[:50])

            # Get transcript
            transcript = await Transcript.find_one(Transcript.video_id == video_id)
            storage = AzureBlobStorage()
            temp_dir = tempfile.mkdtemp(prefix="clipper_render_")

            # Download edited clip
            local_clip = os.path.join(temp_dir, f"clip_{clip_id}.mp4")
            await storage.download_to_file(
                blob_name=clip.blob_name,
                local_path=local_clip,
                container="processed-clips",
            )

            final_output = local_clip

            # Generate and burn captions if transcript available
            if transcript and job_config.add_captions:
                words = transcript.get_words_between(clip.start_time, clip.end_time)

                if words and len(words) >= 2:
                    # Load caption style
                    style = None
                    if job_config.caption_style_id:
                        style = await CaptionStyle.get(job_config.caption_style_id)
                    if not style:
                        style = await CaptionStyle.find_one(CaptionStyle.is_default == True)

                    # Generate ASS subtitles
                    renderer = CaptionRenderer(style)
                    ass_path = os.path.join(temp_dir, f"captions_{clip_id}.ass")
                    renderer.generate_ass_file(
                        words=words,
                        output_path=ass_path,
                        clip_start_offset=clip.start_time,
                    )

                    # Burn subtitles into video
                    final_output = os.path.join(temp_dir, f"final_{clip_id}.mp4")
                    cmd = build_subtitle_burn_command(
                        input_path=local_clip,
                        subtitle_path=ass_path,
                        output_path=final_output,
                    )

                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=300
                    )

                    if result.returncode != 0:
                        logger.warning(
                            "Subtitle burn failed, using clip without captions",
                            clip_id=clip_id,
                            stderr=result.stderr[-200:],
                        )
                        final_output = local_clip
                    else:
                        clip.has_captions = True

                    logger.info("Captions applied", clip_id=clip_id, words_count=len(words))
                else:
                    logger.info("No words in time range, skipping captions", clip_id=clip_id)

            # Upload final clip
            final_blob = f"final_{clip_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4"
            final_url = await storage.upload_from_file(
                local_path=final_output,
                blob_name=final_blob,
                content_type="video/mp4",
            )

            # Update clip
            clip.blob_url = final_url
            clip.blob_name = final_blob
            clip.status = "completed"
            clip.rendered_at = datetime.utcnow()
            await clip.save()

            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)

            # Check job completion
            total = await Clip.find(Clip.job_id == job_id).count()
            completed = await Clip.find(
                Clip.job_id == job_id, Clip.status == "completed"
            ).count()
            failed = await Clip.find(
                Clip.job_id == job_id, Clip.status == "failed"
            ).count()
            done = completed + failed

            job.total_clips_rendered = completed

            progress = (done / total * 100) if total > 0 else 100
            PipelineOrchestrator.update_step(job, "render", "running", progress)

            if done >= total:
                # ALL clips processed — JOB COMPLETE
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                PipelineOrchestrator.update_step(job, "render", "completed", 100)
                await job.save()

                # Calculate total processing time
                processing_time = ""
                if job.started_at:
                    delta = datetime.utcnow() - job.started_at
                    minutes = int(delta.total_seconds() / 60)
                    processing_time = f" in {minutes} minutes" if minutes > 0 else " in <1 minute"

                logger.info(
                    "🎬 JOB COMPLETE",
                    job_id=job_id,
                    video=video.original_filename,
                    clips_completed=completed,
                    clips_failed=failed,
                    processing_time=processing_time,
                )

                # Send notification
                if not job.notification_sent:
                    notifier = Notifier()
                    await notifier.notify_job_completed(
                        job_id=job_id,
                        video_name=video.original_filename,
                        clips_count=completed,
                        notify_whatsapp=job.notify_whatsapp,
                        notify_telegram=job.notify_telegram,
                        whatsapp_number=job.whatsapp_number,
                    )
                    job.notification_sent = True
                    await job.save()

                    if failed > 0:
                        await notifier.send_telegram(
                            f"⚠️ Note: {failed} out of {total} clips failed to render. "
                            f"Check the dashboard for details."
                        )
            else:
                await job.save()

            return {
                "status": "success",
                "clip_id": clip_id,
                "has_captions": clip.has_captions,
                "job_progress": f"{done}/{total}",
            }

        except Exception as e:
            logger.error("Render failed", clip_id=clip_id, error=str(e))
            clip.status = "failed"
            await clip.save()
            PipelineOrchestrator.update_step(job, "render", "running", 0, error=str(e))
            await job.save()

            if self.request.retries < self.max_retries:
                raise self.retry(exc=e)

    asyncio.run(_run())
