"""
Jobs API Endpoints
======================
Monitor, cancel, and retry processing jobs.
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.models.job import Job
from app.models.video import Video
from app.schemas.responses import JobResponse
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("api.jobs")


@router.get("/", response_model=list[JobResponse])
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter: queued, processing, completed, failed, cancelled"),
    video_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
):
    """List jobs with optional filters."""
    query = {}
    if status:
        query["status"] = status
    if video_id:
        query["video_id"] = video_id

    jobs = await Job.find(query).sort("-created_at").skip(skip).limit(limit).to_list()
    return [JobResponse.from_job(j) for j in jobs]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """
    Get detailed job status with per-step progress.

    Returns real-time progress including:
    - Current step and its progress
    - Overall weighted progress
    - Per-step metadata (e.g. transcription language, clips found)
    """
    job = await Job.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.from_job(job)


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancel a running job.
    In-progress tasks will finish their current step but not proceed further.
    """
    job = await Job.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in ("completed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status: {job.status}",
        )

    job.status = "cancelled"
    job.error_message = "Cancelled by user"
    await job.save()

    logger.info("Job cancelled", job_id=job_id)

    return {
        "message": "Job cancelled. In-progress steps will complete but pipeline will stop.",
        "job_id": job_id,
    }


@router.post("/{job_id}/retry")
async def retry_job(job_id: str):
    """
    Retry a failed job from the failed step.
    Resets error state and re-enqueues the appropriate task.
    """
    job = await Job.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "failed":
        raise HTTPException(
            status_code=400,
            detail=f"Can only retry failed jobs. Current status: {job.status}",
        )

    # Find the failed step
    failed_step = None
    for step in job.steps:
        if step["status"] == "failed":
            failed_step = step["name"]
            step["status"] = "pending"
            step["progress"] = 0
            step["error"] = None
            break

    # Reset job status
    job.status = "processing"
    job.error_message = None
    job.retry_count += 1
    await job.save()

    # Re-enqueue the appropriate task
    video = await Video.get(job.video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Associated video not found")

    if failed_step == "download":
        from app.workers.tasks.download import download_video
        download_video.delay(str(video.id), str(job.id), video.source_url)
    elif failed_step == "transcribe":
        from app.workers.tasks.transcribe import transcribe_video
        transcribe_video.delay(str(video.id), str(job.id))
    elif failed_step == "analyze":
        from app.models.transcript import Transcript
        transcript = await Transcript.find_one(Transcript.video_id == str(video.id))
        if transcript:
            from app.workers.tasks.analyze import analyze_highlights
            analyze_highlights.delay(str(video.id), str(job.id), str(transcript.id))
        else:
            from app.workers.tasks.transcribe import transcribe_video
            transcribe_video.delay(str(video.id), str(job.id))
    elif failed_step in ("edit", "render"):
        # Re-process failed clips
        from app.models.clip import Clip
        failed_clips = await Clip.find(
            Clip.job_id == str(job.id),
            Clip.status == "failed",
        ).to_list()

        if failed_step == "edit":
            from app.workers.tasks.edit_video import edit_clip
            for clip in failed_clips:
                clip.status = "pending"
                await clip.save()
                edit_clip.delay(str(video.id), str(job.id), str(clip.id))
        else:
            from app.workers.tasks.render import render_clip
            for clip in failed_clips:
                clip.status = "edited"
                await clip.save()
                render_clip.delay(str(video.id), str(job.id), str(clip.id))

    logger.info("Job retried", job_id=job_id, from_step=failed_step)

    return {
        "message": f"Job retried from step: {failed_step}",
        "job_id": job_id,
        "retry_count": job.retry_count,
    }


@router.get("/stats/dashboard")
async def dashboard_stats():
    """
    Get aggregate statistics for the dashboard.
    """
    from app.models.clip import Clip

    total_videos = await Video.count()
    total_jobs = await Job.count()
    total_clips = await Clip.count()
    processing = await Job.find(Job.status == "processing").count()
    completed = await Job.find(Job.status == "completed").count()
    failed = await Job.find(Job.status == "failed").count()
    approved = await Clip.find(Clip.review_status == "approved").count()
    rejected = await Clip.find(Clip.review_status == "rejected").count()

    # Average processing time
    completed_jobs = await Job.find(
        Job.status == "completed",
        Job.started_at != None,
        Job.completed_at != None,
    ).to_list()

    avg_time = 0.0
    if completed_jobs:
        total_time = sum(
            (j.completed_at - j.started_at).total_seconds()
            for j in completed_jobs
        )
        avg_time = round(total_time / len(completed_jobs) / 60, 1)

    return {
        "total_videos": total_videos,
        "total_jobs": total_jobs,
        "total_clips": total_clips,
        "jobs_processing": processing,
        "jobs_completed": completed,
        "jobs_failed": failed,
        "avg_processing_time_minutes": avg_time,
        "clips_approved": approved,
        "clips_rejected": rejected,
    }
