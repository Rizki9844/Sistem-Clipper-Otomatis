"""
AI Analysis Worker Task
=========================
Celery task: Use LLM to analyze transcript and
identify high-potential highlight segments.

Pipeline: Download → Transcribe → [Analyze] → Edit → Render
"""

import asyncio
from datetime import datetime

from app.workers.celery_app import celery_app
from app.logging_config import get_logger

logger = get_logger("task.analyze")


@celery_app.task(
    bind=True,
    name="app.workers.tasks.analyze.analyze_highlights",
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=240,
    time_limit=300,
)
def analyze_highlights(self, video_id: str, job_id: str, transcript_id: str):
    """
    Task 3/5 in pipeline: AI analysis of transcript.

    Steps:
        1. Load transcript from MongoDB
        2. Send to LLM for highlight detection
        3. Filter by min_highlight_score from job config
        4. Create Clip records for each highlight
        5. Fan-out: enqueue editing tasks for each clip
    """
    async def _run():
        from app.database import init_database
        from app.models.video import Video
        from app.models.job import Job
        from app.models.transcript import Transcript
        from app.models.clip import Clip
        from app.services.ai_analyzer import AIAnalyzer
        from app.services.pipeline import PipelineOrchestrator, JobConfig
        from app.exceptions import NoHighlightsFoundError

        await init_database()

        video = await Video.get(video_id)
        job = await Job.get(job_id)
        transcript = await Transcript.get(transcript_id)

        if not all([video, job, transcript]):
            raise ValueError("Missing video, job, or transcript")

        job_config = JobConfig.from_dict(job.config)

        try:
            await PipelineOrchestrator.check_cancellation(job)

            job.current_step = "analyze"
            PipelineOrchestrator.update_step(job, "analyze", "running", 10)
            await job.save()

            logger.info(
                "Starting AI analysis",
                video_id=video_id,
                transcript_segments=len(transcript.segments),
                max_clips=job_config.max_clips,
            )

            # Run AI analysis
            analyzer = AIAnalyzer()
            segments_data = [
                {"text": seg.text, "start": seg.start, "end": seg.end}
                for seg in transcript.segments
            ]

            result = await analyzer.analyze_transcript(
                transcript_text=transcript.full_text,
                transcript_segments=segments_data,
                video_duration=video.duration_seconds or 0,
                max_segments=job_config.max_clips,
            )

            PipelineOrchestrator.update_step(job, "analyze", "running", 60)
            await job.save()

            # Filter by minimum score
            qualified = [
                seg for seg in result.segments
                if seg.score >= job_config.min_highlight_score
            ]

            if not qualified:
                # Lower threshold and try again
                qualified = [
                    seg for seg in result.segments
                    if seg.score >= max(1.0, job_config.min_highlight_score - 2.0)
                ]
                if not qualified:
                    raise NoHighlightsFoundError(
                        "AI could not find any segments meeting the quality threshold. "
                        "Try lowering min_highlight_score or using a different video.",
                        details={
                            "total_found": len(result.segments),
                            "min_score": job_config.min_highlight_score,
                            "highest_score": max((s.score for s in result.segments), default=0),
                        },
                    )

            logger.info(
                "Highlights found",
                total_found=len(result.segments),
                qualified=len(qualified),
                min_score=job_config.min_highlight_score,
                themes=result.content_themes,
            )

            # Create Clip records
            clip_ids = []
            for segment in qualified:
                clip = Clip(
                    video_id=video_id,
                    job_id=job_id,
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    duration=segment.end_time - segment.start_time,
                    highlight_score=segment.score,
                    hook_text=segment.hook_text,
                    category=segment.category,
                    ai_reasoning=segment.reasoning,
                    orientation="portrait" if job_config.crop_to_portrait else "landscape",
                    width=1080 if job_config.crop_to_portrait else (video.width or 1920),
                    height=1920 if job_config.crop_to_portrait else (video.height or 1080),
                    caption_style_id=job_config.caption_style_id,
                    status="pending",
                )
                await clip.insert()
                clip_ids.append(str(clip.id))

            # Update job
            job.total_clips_found = len(clip_ids)
            job.clip_ids = clip_ids
            PipelineOrchestrator.update_step(
                job, "analyze", "completed", 100,
                metadata={
                    "total_analyzed": len(result.segments),
                    "qualified_clips": len(qualified),
                    "themes": result.content_themes,
                    "summary": result.overall_summary[:200],
                }
            )
            await job.save()

            # Fan-out: enqueue editing tasks for each clip
            from app.workers.tasks.edit_video import edit_clip
            for clip_id in clip_ids:
                edit_clip.delay(video_id, job_id, clip_id)

            logger.info(
                "Analysis complete, editing tasks enqueued",
                video_id=video_id,
                clips_count=len(clip_ids),
            )

            return {
                "status": "success",
                "highlights_found": len(clip_ids),
                "themes": result.content_themes,
            }

        except NoHighlightsFoundError as e:
            logger.warning("No highlights found", video_id=video_id, error=str(e))
            job.status = "completed"  # Not a failure — just no good clips
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            PipelineOrchestrator.update_step(job, "analyze", "completed", 100, error=str(e))
            await job.save()

            # Still notify the user
            from app.services.notifier import Notifier
            notifier = Notifier()
            await notifier.notify_job_completed(
                job_id=job_id,
                video_name=video.original_filename,
                clips_count=0,
                notify_telegram=job.notify_telegram,
            )

        except Exception as e:
            logger.error("Analysis failed", video_id=video_id, error=str(e))
            job.error_message = str(e)
            PipelineOrchestrator.update_step(job, "analyze", "failed", 0, error=str(e))
            await job.save()

            if self.request.retries >= self.max_retries:
                job.status = "failed"
                await job.save()
            else:
                raise self.retry(exc=e)

    asyncio.run(_run())
