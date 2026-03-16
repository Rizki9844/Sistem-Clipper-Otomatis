"""
Celery Task: Publish Clip to Social Media
==========================================
Async task yang dieksekusi oleh worker untuk upload video ke platform.
"""

from datetime import datetime
import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.workers.tasks.publish.publish_clip_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="rendering",  # gunakan rendering queue (low priority)
)
def publish_clip_task(self, publish_job_id: str):
    """
    Upload clip to the target social media platform.
    Fetches video from Azure Blob Storage and POSTs to platform API.
    """
    import asyncio

    async def _run():
        from app.database import init_database
        from app.models.publish_job import PublishJob
        from app.models.clip import Clip
        from app.services.publisher import publish_to_platform
        from app.services.storage import get_download_url

        await init_database()

        pub_job = await PublishJob.get(publish_job_id)
        if not pub_job:
            logger.error(f"PublishJob {publish_job_id} not found")
            return

        pub_job.status = "processing"
        pub_job.updated_at = datetime.utcnow()
        await pub_job.save()

        try:
            clip = await Clip.get(pub_job.clip_id)
            if not clip:
                raise ValueError(f"Clip {pub_job.clip_id} not found")

            if not clip.output_blob_path:
                raise ValueError("Clip has no output video path")

            # Get temporary download URL from Azure Blob
            video_url = await get_download_url(
                clip.output_blob_path,
                container="processed-clips",
                expiry_hours=2,
            )

            # Publish to platform
            post_url = await publish_to_platform(pub_job, clip, video_url)

            pub_job.status = "published"
            pub_job.platform_post_url = post_url
            pub_job.published_at = datetime.utcnow()

        except Exception as exc:
            logger.exception(f"Publish failed for job {publish_job_id}: {exc}")
            pub_job.retry_count += 1

            if pub_job.retry_count < 3:
                pub_job.status = "pending"
                pub_job.updated_at = datetime.utcnow()
                await pub_job.save()
                raise self.retry(exc=exc, countdown=60 * pub_job.retry_count)

            pub_job.status = "failed"
            pub_job.error_message = str(exc)

        pub_job.updated_at = datetime.utcnow()
        await pub_job.save()

    asyncio.get_event_loop().run_until_complete(_run())
