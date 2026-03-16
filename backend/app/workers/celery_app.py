"""
Celery Application Configuration
====================================
Distributed task queue using Celery + Redis.
Configured for Azure Cache for Redis in production.
"""

from celery import Celery
from app.config import settings

# ---- Create Celery App ----
celery_app = Celery(
    "auto_clipper",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    # ---- include publish task ----
    include=[
        "app.workers.tasks.download",
        "app.workers.tasks.transcribe",
        "app.workers.tasks.analyze",
        "app.workers.tasks.edit_video",
        "app.workers.tasks.render",
        "app.workers.tasks.publish",
    ],
)

# ---- Celery Configuration ----
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,

    # Retry policy
    task_default_retry_delay=60,
    task_max_retries=3,

    # Result backend
    result_expires=86400,

    # Task routing (priority queues)
    task_routes={
        "app.workers.tasks.download.*": {"queue": "download"},
        "app.workers.tasks.transcribe.*": {"queue": "transcription"},
        "app.workers.tasks.analyze.*": {"queue": "analysis"},
        "app.workers.tasks.edit_video.*": {"queue": "editing"},
        "app.workers.tasks.render.*": {"queue": "rendering"},
        "app.workers.tasks.publish.*": {"queue": "rendering"},  # low priority
    },

    # Priority queue support (0=highest, 9=lowest)
    # Pro/Business jobs sent with priority=0, Free jobs with priority=9
    task_queue_max_priority=9,
    task_default_priority=5,

    # Rate limiting
    task_annotations={
        "app.workers.tasks.download.download_video": {
            "rate_limit": "3/m",
        },
        "app.workers.tasks.transcribe.transcribe_video": {
            "rate_limit": "2/m",
        },
        "app.workers.tasks.analyze.analyze_highlights": {
            "rate_limit": "10/m",
        },
    },

    # Concurrency
    worker_concurrency=2,

    # Task time limits
    task_soft_time_limit=600,
    task_time_limit=900,

    # SSL/TLS for Upstash Redis (rediss:// protocol)
    broker_use_ssl={
        "ssl_cert_reqs": None,
    } if settings.CELERY_BROKER_URL.startswith("rediss://") else None,
    redis_backend_use_ssl={
        "ssl_cert_reqs": None,
    } if settings.CELERY_RESULT_BACKEND.startswith("rediss://") else None,
)

# ---- Sentry integration for worker errors ----
if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[CeleryIntegration()],
        traces_sample_rate=0.1,
        environment=settings.APP_ENV,
    )
