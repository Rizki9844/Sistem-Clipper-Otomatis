# ============================================================
# AutoClipperPro Backend — Production Dockerfile
# ============================================================
# Multi-stage build: Python 3.11 + FFmpeg + yt-dlp + MediaPipe
# Target: Heroku / Azure Container Instances
# ============================================================

FROM python:3.11-slim AS base

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ---- System Dependencies ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---- Install yt-dlp ----
RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp \
    && chmod a+rx /usr/local/bin/yt-dlp

# ---- Working Directory ----
WORKDIR /app

# ---- Python Dependencies ----
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Application Code ----
COPY backend/ .

# ---- Health Check ----
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# ---- Default Command (API server) ----
# Heroku sets $PORT dynamically
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2

EXPOSE 8000
