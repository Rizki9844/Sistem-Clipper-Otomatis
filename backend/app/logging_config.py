"""
Structured Logging Configuration
====================================
Uses structlog for structured JSON logging in production
and rich pretty-printed logs in development.
"""

import logging
import sys

import structlog
from app.config import settings


def setup_logging():
    """
    Configure structured logging for the entire application.

    - Development: Pretty-printed, colorful console output
    - Production: JSON-formatted for Loki/ELK ingestion
    """
    # Shared processors for all modes
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.is_production:
        # Production: JSON output for log aggregation
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Development: Rich console output
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.processors.format_exc_info,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )

    # Also configure standard library logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO if settings.is_production else logging.DEBUG,
    )


def get_logger(name: str | None = None, **initial_context) -> structlog.BoundLogger:
    """
    Get a structured logger with optional initial context.

    Usage:
        logger = get_logger("video_editor", job_id="abc123")
        logger.info("Starting edit", clip_index=0, duration=45.5)
        logger.error("FFmpeg failed", returncode=1, stderr="...")

    Output (dev):
        2026-03-09T10:00:00Z [info] Starting edit  job_id=abc123 clip_index=0 duration=45.5
    Output (prod JSON):
        {"event": "Starting edit", "level": "info", "job_id": "abc123", "clip_index": 0}
    """
    logger = structlog.get_logger(name)
    if initial_context:
        logger = logger.bind(**initial_context)
    return logger
