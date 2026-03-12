"""
Application Configuration
==========================
Centralized settings using Pydantic BaseSettings.
Reads from .env file and environment variables.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Main application settings."""

    # --- Application ---
    APP_NAME: str = "AutoClipperPro"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-in-production"

    # --- MongoDB ---
    MONGODB_URL: str = "mongodb://clipper_admin:clipper_dev_password@localhost:27017/clipper_db?authSource=admin"
    MONGODB_DB_NAME: str = "clipper_db"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # --- Azure Blob Storage ---
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER_RAW: str = "raw-videos"
    AZURE_STORAGE_CONTAINER_CLIPS: str = "processed-clips"
    AZURE_STORAGE_CONTAINER_THUMBNAILS: str = "thumbnails"

    # --- Google Gemini (FREE — 1M tokens/day) ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-pro-preview-05-06"
    WHISPER_MODEL: str = "base"

    # --- Sentry ---
    SENTRY_DSN: Optional[str] = None

    # --- WhatsApp (Meta Cloud API) ---
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v18.0"
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""

    # --- Telegram Bot ---
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # --- FFmpeg ---
    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"

    # --- yt-dlp ---
    YTDLP_PATH: str = "yt-dlp"
    YTDLP_MAX_DOWNLOAD_RATE: str = "50M"

    # --- Processing Limits ---
    MAX_VIDEO_SIZE_MB: int = 500
    MAX_VIDEO_DURATION_MINUTES: int = 120
    MAX_CONCURRENT_JOBS: int = 3
    CLIP_MIN_DURATION_SECONDS: int = 15
    CLIP_MAX_DURATION_SECONDS: int = 90

    # --- Quality Defaults ---
    DEFAULT_QUALITY_PRESET: str = "balanced"
    DEFAULT_TARGET_ASPECT: str = "9:16"
    DEFAULT_FACE_TRACKING: bool = True
    DEFAULT_ADD_CAPTIONS: bool = True

    # --- CORS ---
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://*.vercel.app",
    ]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def max_video_size_bytes(self) -> int:
        return self.MAX_VIDEO_SIZE_MB * 1024 * 1024


# Singleton instance
settings = Settings()
