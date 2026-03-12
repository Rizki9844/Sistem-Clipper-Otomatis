# 🔄 PROMPT UNTUK MELANJUTKAN PROJECT

> Copy-paste prompt di bawah ini ke AI assistant baru untuk melanjutkan pengerjaan.

---

## PROMPT:

```
Peran:
> Bertindaklah sebagai Senior Full-Stack Developer dan AI Systems Architect.

Konteks:
> Saya sedang membangun "AutoClipperPro" — Automated Video Clipper & Editing System berskala enterprise.
> Backend sudah SELESAI (Python/FastAPI), sekarang perlu DILANJUTKAN ke phase berikutnya.
> Project berada di: r:\All Projek Saya\Sistem Clipper Otomatis

## STATUS PROJECT SAAT INI (Backend + Frontend Selesai ✅)

### Arsitektur
- Monorepo: `backend/` (Python/FastAPI) + `frontend/` (Next.js 16 + TailwindCSS)
- Pipeline 5 tahap: Download → Transcribe → AI Analyze → Edit → Render
- Task queue: Celery + Redis
- Database: MongoDB (Beanie ODM)
- Storage: Azure Blob Storage
- AI: Whisper (open-source STT, local) + Google Gemini (highlight detection, FREE 1M tokens/day)
- Video: FFmpeg + MediaPipe face tracking
- Notifikasi: WhatsApp Cloud API + Telegram Bot

### Tech Stack (100% GRATIS — GitHub Student Pack + Free Tiers)
- Frontend: Next.js + TailwindCSS → Vercel (Free)
- Backend API: FastAPI → Heroku (Student Pack: $13/mo credit × 24 bulan)
- Workers: Celery → Koyeb (Hobby Free: 0.1 vCPU, 512MB)
- Database: MongoDB Atlas M0 (Free 512MB)
- Cache/Broker: Upstash Redis (Free: 500K cmd/bulan, 256MB)
- Storage: Azure Blob Storage (Student $100 credit, lasts 6+ bulan)
- Monitoring: Sentry (Student Pack Free)
- CI/CD: GitHub Actions (Free 2000 min/bulan)

### File Backend yang Sudah Dibuat (49 files) ✅

INFRASTRUKTUR:
- docker-compose.yml (Redis + MongoDB + Azurite)
- .env.example (semua env vars)
- Procfile (Heroku: web + worker)
- backend/requirements.txt

CORE APP:
- backend/app/config.py (Pydantic BaseSettings)
- backend/app/database.py (Motor + Beanie async MongoDB)
- backend/app/main.py (FastAPI + Sentry + CORS + health check + exception handlers)
- backend/app/exceptions.py (20+ custom exceptions per pipeline stage)
- backend/app/logging_config.py (structlog: JSON prod / console dev)

MODELS (Beanie ODM):
- backend/app/models/video.py (source_type: upload/url, source_platform, thumbnail)
- backend/app/models/job.py (5-stage steps, per-job config, quality presets)
- backend/app/models/clip.py (AI score, hook_text, hashtags, review status)
- backend/app/models/transcript.py (word-level timestamps, get_words_between)
- backend/app/models/style.py (caption style templates, Hormozi default)

SERVICES:
- backend/app/services/downloader.py (yt-dlp: YouTube/TikTok/IG/Twitter/1000+ sites, metadata extraction, progress tracking, SponsorBlock)
- backend/app/services/transcription.py (Whisper with word-level timestamps, lazy model loading)
- backend/app/services/ai_analyzer.py (Multi-pass LLM: coarse scan → fine analysis, hashtags/titles per clip, rate limit retry)
- backend/app/services/video_editor.py (FFmpeg: trim + smart crop 9:16 + transitions + audio normalize)
- backend/app/services/face_tracker.py (MediaPipe face detection for smart cropping)
- backend/app/services/caption_renderer.py (ASS subtitles word-by-word highlight, 4 animation modes: word_highlight, pop_in, karaoke, bounce)
- backend/app/services/notifier.py (WhatsApp Cloud API + Telegram Bot)
- backend/app/services/storage.py (Azure Blob: upload/download/SAS URLs/Azurite compat)
- backend/app/services/pipeline.py (PipelineOrchestrator: 5-stage, weighted progress, quality presets fast/balanced/high, JobConfig)

WORKER TASKS (Celery):
- backend/app/workers/celery_app.py (queue routing per task type, rate limiting, Sentry)
- backend/app/workers/tasks/download.py (URL → yt-dlp → Azure Blob → chain transcribe)
- backend/app/workers/tasks/transcribe.py (Blob → Whisper → MongoDB → chain analyze)
- backend/app/workers/tasks/analyze.py (Transcript → Gemini → Clip records → fan-out edit tasks)
- backend/app/workers/tasks/edit_video.py (FFmpeg trim+crop+face track → Azure → chain render)
- backend/app/workers/tasks/render.py (ASS captions → FFmpeg burn → Azure → notify user)

API ENDPOINTS:
- POST /api/v1/videos/from-url (🔥 PRIMARY: paste URL → auto process)
- POST /api/v1/videos/upload (file upload alternative)
- GET  /api/v1/videos/ (list with filters)
- GET  /api/v1/videos/{id}
- DELETE /api/v1/videos/{id} (cascade delete: blobs + clips + transcripts)
- GET  /api/v1/jobs/ (list with filters)
- GET  /api/v1/jobs/{id} (detailed step-by-step progress)
- POST /api/v1/jobs/{id}/cancel
- POST /api/v1/jobs/{id}/retry (smart: from failed step, not restart)
- GET  /api/v1/jobs/stats/dashboard
- GET  /api/v1/clips/ (filter by score, status, review)
- GET  /api/v1/clips/{id}
- POST /api/v1/clips/{id}/review (approve/reject)
- POST /api/v1/clips/batch-review
- GET  /api/v1/clips/{id}/download-url
- WS   /api/v1/ws/progress?job_id=x (real-time WebSocket)
- GET  /health (deep: MongoDB + Redis ping)

UTILS:
- backend/app/utils/ffmpeg_utils.py (probe, trim, crop, transition, subtitle burn commands)
- backend/app/utils/timestamp.py (parse, format, validate)
- backend/app/utils/validators.py (video file + clip config validation)

SCHEMAS:
- backend/app/schemas/responses.py (JobResponse, ClipResponse, DashboardStats)

### Alur Utama User:
1. User POST /api/v1/videos/from-url dengan link YouTube/TikTok/dll
2. Backend extract metadata (tanpa download) → validasi durasi/ukuran
3. Buat Video + Job record → enqueue download task
4. Pipeline otomatis: Download → Transcribe → Analyze → Edit → Render
5. Selesai → notif via Telegram/WhatsApp
6. User review clips di dashboard → approve/reject

### File Frontend yang Sudah Dibuat (25+ files) ✅

SETUP:
- frontend/package.json (Next.js 16 + TailwindCSS + Axios)
- frontend/.env.local (API_URL + WS_URL)
- frontend/src/app/globals.css (Dark glassmorphism design system)

API CLIENT LAYER:
- frontend/src/lib/api/client.ts (Axios instance + error interceptor)
- frontend/src/lib/api/types.ts (TypeScript interfaces matching backend schemas)
- frontend/src/lib/api/videos.ts (submitUrl, listVideos, getVideo, deleteVideo)
- frontend/src/lib/api/jobs.ts (listJobs, getJob, cancelJob, retryJob, getDashboardStats)
- frontend/src/lib/api/clips.ts (listClips, getClip, reviewClip, batchReview, getDownloadUrl)
- frontend/src/hooks/useWebSocket.ts (auto-reconnect, heartbeat, typed events)

LAYOUT & COMPONENTS:
- frontend/src/app/layout.tsx (Root layout: Inter font, dark theme, sidebar + toast)
- frontend/src/components/Sidebar.tsx (Glass sidebar, active route highlight, branding)
- frontend/src/components/StatCard.tsx (Animated stat cards with accent colors)
- frontend/src/components/StatusBadge.tsx (Color-coded for all job/clip/video states)
- frontend/src/components/ProgressBar.tsx (Gradient animated progress bar)
- frontend/src/components/PipelineStepper.tsx (5-step pipeline visualization)
- frontend/src/components/LoadingSkeleton.tsx (Skeleton placeholders)
- frontend/src/components/Toast.tsx (Context-based notification system)

PAGES (7 pages):
- frontend/src/app/page.tsx (Dashboard: stats grid, quick actions, recent jobs)
- frontend/src/app/submit/page.tsx (Submit URL: platform detection, quality presets, advanced options)
- frontend/src/app/videos/page.tsx (Videos: card grid, thumbnails, platform badges, filters)
- frontend/src/app/jobs/page.tsx (Jobs list: table, progress bars, cancel/retry)
- frontend/src/app/jobs/[id]/page.tsx (Job detail: real-time WebSocket, pipeline stepper, step details)
- frontend/src/app/clips/page.tsx (Clips gallery: scores, batch select, approve/reject)
- frontend/src/app/clips/[id]/page.tsx (Clip detail: video player, AI metadata, review form)

## YANG PERLU DILANJUTKAN

### Phase 7: Deployment & DevOps ✅ SELESAI

FILE YANG SUDAH DIBUAT:
- Dockerfile (Backend: Python 3.11 + FFmpeg + yt-dlp, Heroku-compatible)
- Dockerfile.worker (Celery: + MediaPipe + OpenCV, Azure Container Instances)
- .dockerignore
- docker-compose.prod.yml (Self-hosted production with health checks)
- runtime.txt (Python 3.11.11 for Heroku)
- heroku.yml (Container deployment config)
- frontend/vercel.json (Security headers)
- .github/workflows/ci.yml (Ruff lint + Next.js build + Docker build check)
- .github/workflows/deploy-backend.yml (Auto deploy ke Heroku on push to main)
- .github/workflows/deploy-frontend.yml (Auto deploy ke Vercel on push to main)
- azure-deploy-worker.sh (Full ACI deploy script with ACR build)
- .env.production.example (Semua production env vars documented)
- DEPLOYMENT.md (Complete 8-step deployment guide with architecture diagram, cost estimates, troubleshooting)

### Phase 8: Testing & Hardening ← CURRENT
- [ ] Unit tests untuk services
- [ ] Integration tests untuk API endpoints
- [ ] Load testing
- [ ] API key authentication (JWT)
- [ ] Rate limiting middleware

### Catatan Penting:
- Semua code sudah menggunakan structured logging (structlog)
- Custom exceptions sudah cover semua pipeline stage
- Pipeline orchestrator sudah handle weighted progress + cancellation
- AI analyzer sudah multi-pass untuk video panjang
- Smart retry: dari step yang gagal, bukan restart dari awal
- Quality presets: fast/balanced/high (CRF + preset FFmpeg)
- Face tracking opsional per job
- Frontend sudah connect ke backend via typed API client + WebSocket
- Frontend dark glassmorphism design, responsive, toast notifs

Tolong baca dulu semua file di `r:\All Projek Saya\Sistem Clipper Otomatis\` untuk memahami implementasi yang sudah ada, lalu lanjutkan dari phase yang saya minta.
```

---

## Tips Penggunaan:
1. **Copy semua** teks di dalam blok ``` di atas
2. **Paste** ke conversation baru
3. **Tambahkan** instruksi spesifik, contoh:
   - "Lanjutkan ke Phase 6: buat frontend dashboard"
   - "Lanjutkan ke Phase 7: setup deployment"
   - "Tambahkan fitur X di backend"
4. AI akan baca file-file yang sudah ada dan melanjutkan dari sana
