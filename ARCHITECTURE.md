# AutoClipperPro Architecture

## 1. Gambaran Umum
AutoClipperPro adalah sistem pemrosesan video berbasis pipeline async untuk menghasilkan short clips dari long-form content.

Value flow utama:
1) User submit video/source URL.
2) Sistem transcribe dan analisis highlight dengan AI.
3) Sistem memotong video, merender caption, dan menghasilkan clip siap review/publish.

## 2. High-Level Topology

### Frontend Layer
- Next.js App Router
- Running di Vercel
- Tanggung jawab:
  - Auth session client
  - Submit job
  - Monitor progress
  - Review clips
  - Billing and admin UI

### API Layer
- FastAPI
- Running di Heroku web dyno
- Tanggung jawab:
  - Auth dan authorization
  - Validasi request
  - Buat job dan orkestrasi task async
  - Expose data dan status ke frontend

### Worker Layer
- Celery worker process
- Tanggung jawab:
  - Download, transcribe, analyze, edit, render, publish
  - Update progress dan status job

### Data and Infra Layer
- MongoDB Atlas: source of truth user/job/video/clip
- Redis (Upstash): broker + result backend task
- Azure Blob: raw video dan processed clips
- External AI: Gemini + Whisper

## 3. Domain Model Ringkas

### User Domain
- User
- Plan tier, quota, subscription metadata

### Media Domain
- Video: representasi source input
- Transcript: hasil transcribe + timestamp
- Clip: hasil final/calon hasil pipeline

### Processing Domain
- Job: state machine pipeline
- Step progress and error details

### Publishing Domain
- SocialAccount: token/account platform
- PublishJob: status publish ke platform

## 4. Pipeline States (Konseptual)
- queued
- download
- transcribe
- analyze
- edit
- render
- completed
- failed

Setiap transisi wajib:
- update status di DB
- update progress
- emit log yang dapat ditelusuri via job_id

## 5. End-to-End Data Flow

### A. Submit
1) Frontend kirim request submit.
2) API validasi source + quota.
3) API buat Video + Job.
4) API enqueue pipeline task.

### B. Process
1) Worker download media.
2) Worker transcribe media jadi transcript.
3) Worker analyze transcript jadi candidate highlights.
4) Worker edit per highlight jadi clip.
5) Worker render caption dan finalize output.
6) Worker update Job + Clip records.

### C. Consume
1) Frontend baca status/progress.
2) User review clip.
3) User publish clip (opsional).

## 6. Koneksi Antar Komponen
- Frontend -> API: HTTPS REST.
- API -> Redis: enqueue task.
- Worker -> Redis: consume task.
- API/Worker -> MongoDB: persist state.
- Worker -> Azure Blob: read/write media assets.
- Worker/API -> External APIs: AI/billing/publish.

## 7. Security Boundaries
- JWT untuk auth API.
- CORS hanya origin yang diizinkan.
- Secret hanya via environment variables.
- Jangan expose connection string lengkap di logs/chat.

## 8. Reliability Patterns yang Direkomendasikan
- Retry policy per step dengan batas percobaan.
- Timeout keras untuk task eksternal.
- Idempotency untuk billing webhook dan publish.
- Atomic quota update di DB.
- Dead-letter handling untuk job gagal.

## 9. Operational Checklist Harian
- Health endpoint API: healthy.
- Worker process up.
- Redis connectivity normal.
- Error rate pipeline terkendali.
- Storage growth tidak abnormal.

## 10. Known Architectural Risks
- Beban memory tinggi pada transcribe/edit.
- Rate limit layanan eksternal.
- Token expiry social platform.
- Drift status antara webhook billing dan user plan.

## 11. SLO Awal yang Disarankan
- API availability >= 99.5%.
- Job completion success rate >= 95%.
- Median processing time sesuai durasi input (target internal ditetapkan per tier).

## 12. Evolusi Arsitektur (Next)
- Tambah metrics pipeline per step.
- Tambah lifecycle policy storage raw videos.
- Tambah admin observability dashboard.
- Tambah formal incident runbook.
