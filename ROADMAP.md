# AutoClipperPro Roadmap (30/60/90)

## 1. Tujuan Dokumen
Dokumen ini menjadi sumber roadmap resmi produk dan engineering untuk AutoClipperPro berdasarkan kondisi kode dan deployment saat ini.

## 2. Kondisi Saat Ini (Baseline)
- Platform sudah live dengan arsitektur:
  - Frontend: Next.js (Vercel)
  - Backend API: FastAPI (Heroku)
  - Worker async: Celery
  - DB: MongoDB Atlas
  - Broker/result: Redis (Upstash)
  - Storage: Azure Blob
  - AI: Gemini + Whisper
- Core pipeline sudah berjalan: submit video -> transcribe -> analyze -> edit -> render.
- Fondasi monetization sudah ada: plan tier, billing endpoint, social publish model.

## 3. Prinsip Prioritas
- Reliability dulu, fitur kedua.
- Semua task pipeline harus observable (metrics + traceable error).
- Semua alur billing/publish harus idempotent.
- Semua perubahan punya acceptance criteria yang jelas.

## 4. 30 Hari (Stabilization)

### Epic A: Pipeline Reliability
- Implement retry policy konsisten per step (download/transcribe/analyze/edit/render).
- Tambahkan timeout guard dan fail-fast error classification untuk external dependency.
- Pastikan partial failure tidak membuat job menggantung.

Acceptance criteria:
- Job stuck rate < 2%.
- Setiap failed job punya error reason yang jelas di DB dan log.

### Epic B: Observability
- Tambahkan metrics inti:
  - total job per hari
  - success/fail rate per step
  - durasi p50/p95 tiap step
- Standarkan structured logging (job_id, user_id, step, status).
- Tambahkan dashboard operasional sederhana (manual atau endpoint internal).

Acceptance criteria:
- Semua event step bisa ditelusuri by job_id.
- Ada ringkasan health harian.

### Epic C: Quota and Guardrails
- Audit dan perkuat pemotongan quota user agar atomic.
- Pastikan rate limit endpoint submit dan auth efektif.
- Validasi input URL/source lebih ketat.

Acceptance criteria:
- Tidak ada over-consume quota akibat race condition.
- Invalid source URL ditolak di awal.

## 5. 60 Hari (Product Hardening)

### Epic D: Social Publishing Hardening
- Stabilkan TikTok/Instagram/YouTube publish flow.
- Tambahkan token expiry handling dan refresh/reconnect UX.
- Tambahkan retry idempotent untuk publish job.

Acceptance criteria:
- Publish success rate > 95% untuk akun yang valid.
- Kegagalan publish tidak duplikatif dan bisa retry aman.

### Epic E: Billing Integrity
- Harden webhook processing:
  - dedup event id
  - idempotent subscription update
- Lengkapi flow upgrade/downgrade/cancel.

Acceptance criteria:
- Tidak ada double-processing webhook.
- Status plan user konsisten dengan Stripe.

### Epic F: UX and Review Flow
- Perjelas review clip (pending/approved/rejected) di UI.
- Tambahkan filter dan batch action untuk clips.
- Tingkatkan kejelasan progress pipeline di job detail.

Acceptance criteria:
- Waktu review user turun.
- Komplain "status tidak jelas" berkurang.

## 6. 90 Hari (Scale and Monetization)

### Epic G: Team and Admin Ops
- Finalisasi admin panel untuk monitoring job, user, dan incident.
- Tambahkan fondasi team/workspace (minimal role owner/editor/viewer).

Acceptance criteria:
- Admin bisa triage insiden tanpa akses database langsung.
- Team access dasar berjalan untuk pilot user.

### Epic H: Performance and Cost
- Optimasi cost pipeline (storage lifecycle, cleanup raw video, preset encode).
- Profiling bottleneck step paling mahal (transcribe/edit/render).
- Kebijakan retensi file berdasarkan plan tier.

Acceptance criteria:
- Biaya per video terukur dan menurun.
- Tidak ada growth storage tanpa kontrol.

### Epic I: Launch Readiness
- Definisikan SLO produksi:
  - availability API
  - job completion success rate
  - median processing time
- Siapkan incident runbook v1.

Acceptance criteria:
- Ada SOP jelas untuk 5 insiden teratas.
- Tim bisa response tanpa improvisasi berlebihan.

## 7. Risiko Kritis yang Harus Dipantau
- Worker memory pressure saat transcribe/edit.
- External API limits (Gemini/social APIs).
- Redis connection/latency issues.
- Storage growth tanpa lifecycle management.
- Billing webhook inconsistency.

## 8. Definisi Done per Epic
Epic dianggap selesai jika:
- Feature/guardrail live di environment produksi.
- Ada minimal 1 skenario uji sukses + 1 skenario gagal.
- Ada telemetry/log yang cukup untuk observasi.
- Dokumentasi endpoint/alur diupdate.

## 9. Catatan Eksekusi
- Roadmap ini harus direview mingguan.
- Perubahan prioritas dicatat di section changelog di bawah.

## 10. Changelog Roadmap
- 2026-03-19: Draft awal dibuat dari baseline arsitektur dan deployment saat ini.
