# 🚀 AutoClipperPro — Panduan Deployment Lengkap

> Panduan step-by-step untuk deploy AutoClipperPro dengan **$0/bulan**.
> Ikuti urutan dari Step 1 sampai Step 11.

---

## 📋 Daftar Akun yang Perlu Dibuat

Sebelum mulai, pastikan kamu sudah punya:

| No | Akun | Link Daftar | Butuh Credit Card? |
|----|------|-------------|-------------------|
| 1 | GitHub (Student Pack) | [education.github.com/pack](https://education.github.com/pack) | ❌ Tidak |
| 2 | Google (untuk Gemini) | [aistudio.google.com](https://aistudio.google.com) | ❌ Tidak |
| 3 | MongoDB Atlas | [cloud.mongodb.com](https://cloud.mongodb.com) | ❌ Tidak |
| 4 | Upstash | [console.upstash.com](https://console.upstash.com) | ❌ Tidak |
| 5 | Azure for Students | [azure.microsoft.com/free/students](https://azure.microsoft.com/free/students) | ❌ Tidak |
| 6 | Sentry | [sentry.io](https://sentry.io) | ❌ Tidak |
| 7 | Telegram | Sudah punya | ❌ Tidak |
| 8 | Heroku (Student) | [heroku.com/students](https://www.heroku.com/students) | ❌ Tidak |
| 9 | Koyeb | [app.koyeb.com](https://app.koyeb.com) | ❌ Tidak |
| 10 | Vercel | [vercel.com](https://vercel.com) | ❌ Tidak |

> ✅ **Tidak ada satupun yang butuh credit card!**

---

## 📊 Final Cost: $0/bulan

| Service | Provider | Free Tier |
|---------|----------|-----------|
| Frontend | Vercel | Hobby Plan gratis |
| Backend API | Heroku | $13/bulan credit × 24 bulan |
| Worker | Koyeb | Hobby Free (0.1 vCPU, 512MB) |
| Database | MongoDB Atlas | M0 Free (512MB) |
| Redis | Upstash | 500K commands/bulan |
| Storage | Azure Blob | $100 student credit |
| AI Analysis | Google Gemini | 1M tokens/hari gratis |
| AI STT | Whisper | Open-source, jalan lokal |
| Monitoring | Sentry | Free via Student Pack |
| CI/CD | GitHub Actions | 2000 menit/bulan gratis |

---

## STEP 1: Dapatkan Google Gemini API Key (GRATIS)

**Waktu: ~2 menit**

Gemini dipakai untuk **menganalisis transcript video** dan menentukan bagian mana yang menarik dijadikan clip.

### Langkah-langkah:

1. Buka [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Login dengan akun **Google** kamu
3. Klik **"Create API Key"**
4. Pilih project Google Cloud (atau buat baru — gratis)
5. Klik **"Create API Key in existing project"**
6. Akan muncul API key seperti: `AIzaSyB...`
7. **Copy dan simpan** key ini — nanti dipakai di Step 7 & 8

### Free Tier Gemini:
- **15 requests per menit**
- **1.000.000 tokens per hari** (cukup untuk ~500+ video per hari!)
- Model: **gemini-2.5-pro** (model terkuat, gratis!)

### Verifikasi:
```bash
# Test API key kamu (ganti YOUR_API_KEY):
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello, respond with OK"}]}]}'
```
Kalau response berisi "OK" → API key aktif ✅

---

## STEP 2: Setup MongoDB Atlas (Database — GRATIS)

**Waktu: ~5 menit**

MongoDB Atlas menyimpan semua data: video records, job progress, clips, transcripts.

### Langkah-langkah:

1. Buka [cloud.mongodb.com](https://cloud.mongodb.com) → **Sign up** (bisa pakai Google account)

2. **Create a Cluster:**
   - Klik **"Build a Database"** atau **"Create"**
   - Pilih **M0 FREE** (jangan pilih yang lain!)
   - Provider: **AWS** (default)
   - Region: Pilih **Singapore** (ap-southeast-1) — paling dekat ke Indonesia
   - Cluster Name: `autoclipperpro` (atau biarkan default)
   - Klik **"Create Cluster"**

3. **Buat Database User:**
   - Menu kiri → **Database Access**
   - Klik **"Add New Database User"**
   - Authentication: **Password**
   - Username: `clipper_admin`
   - Password: Klik **"Auto Generate"** → **copy password ini!**
   - Database User Privileges: **Read and write to any database**
   - Klik **"Add User"**

4. **Izinkan Koneksi dari Mana Saja:**
   - Menu kiri → **Network Access**
   - Klik **"Add IP Address"**
   - Klik **"Allow Access from Anywhere"** (ini set `0.0.0.0/0`)
   - Klik **"Confirm"**
   - ⚠️ Kenapa 0.0.0.0/0? Karena Heroku dan Koyeb pakai dynamic IP

5. **Ambil Connection String:**
   - Menu kiri → **Database** → Klik **"Connect"** pada cluster kamu
   - Pilih **"Drivers"**
   - Copy connection string (format):
     ```
     mongodb+srv://clipper_admin:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
     ```
   - **Ganti `<password>`** dengan password yang kamu buat di step 3
   - **Tambahkan nama database** setelah `.net/`:
     ```
     mongodb+srv://clipper_admin:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/autoclipperpro?retryWrites=true&w=majority
     ```

### Simpan:
```
MONGODB_URL=mongodb+srv://clipper_admin:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/autoclipperpro?retryWrites=true&w=majority
MONGODB_DB_NAME=autoclipperpro
```

---

## STEP 3: Setup Upstash Redis (Message Broker — GRATIS)

**Waktu: ~3 menit**

Redis dipakai sebagai **message broker** untuk Celery task queue (menghubungkan backend API dengan worker).

### Langkah-langkah:

1. Buka [console.upstash.com](https://console.upstash.com) → **Sign up with GitHub**

2. **Create Redis Database:**
   - Klik **"Create Database"**
   - Name: `autoclipperpro`
   - Type: **Regional**
   - Region: **Singapore** (ap-southeast-1)
   - ⚠️ **Jangan centang** "TLS (SSL)" kalau diminta — biarkan default
   - Klik **"Create"**

3. **Copy Connection Details:**
   - Setelah database dibuat, buka tab **"Details"**
   - Cari bagian **"REST API"** atau **"Redis"**
   - Copy **Endpoint** dan **Password**
   - URL akan berbentuk: `rediss://default:XXXXXXX@xxxx.upstash.io:6379`

4. **Pastikan copy URL format yang benar:**
   - Cari di halaman database: **"Connect your database"** atau **".env"** tab
   - Ambil yang format `UPSTASH_REDIS_REST_URL` atau Redis URL

### Simpan:
```
REDIS_URL=rediss://default:YOUR_PASSWORD@your-endpoint.upstash.io:6379
CELERY_BROKER_URL=rediss://default:YOUR_PASSWORD@your-endpoint.upstash.io:6379/0
CELERY_RESULT_BACKEND=rediss://default:YOUR_PASSWORD@your-endpoint.upstash.io:6379/1
```

### Free Tier:
- **500.000 commands per bulan** — cukup banget!
- 256MB storage
- 1 database per akun

---

## STEP 4: Setup Azure Blob Storage ($100 Student Credit)

**Waktu: ~10 menit**

Azure Blob Storage menyimpan **file video mentah dan clips yang sudah diproses**.

### 4a. Activate Azure for Students

1. Buka [azure.microsoft.com/free/students](https://azure.microsoft.com/free/students)
2. Klik **"Start Free"**
3. Login dengan akun **sekolah/universitas** kamu (email .edu / .ac.id)
4. Verifikasi status student → Kamu dapat **$100 credit, tanpa credit card!**
5. Klik **"Go to Azure Portal"** → [portal.azure.com](https://portal.azure.com)

### 4b. Buat Storage Account

1. Di Azure Portal, klik **"+ Create a Resource"** (kiri atas)
2. Search: **"Storage Account"** → klik **"Create"**
3. Isi form:
   - **Subscription**: Azure for Students
   - **Resource Group**: Klik "Create new" → nama: `autoclipperpro-rg`
   - **Storage account name**: `autoclipperstore` (harus unique, lowercase, tanpa spasi)
   - **Region**: **(Asia Pacific) Southeast Asia**
   - **Performance**: Standard
   - **Redundancy**: **LRS** (Locally-redundant — paling murah)
4. Klik **"Review + Create"** → **"Create"**
5. Tunggu ~1 menit sampai deployment selesai

### 4c. Buat 3 Containers

1. Buka Storage Account yang baru dibuat
2. Menu kiri → **"Containers"**
3. Klik **"+ Container"** dan buat 3 container:

| Container Name | Public Access Level |
|----------------|-------------------|
| `raw-videos` | Private (no anonymous access) |
| `processed-clips` | Private (no anonymous access) |
| `thumbnails` | Blob (anonymous read for blobs only) |

### 4d. Ambil Connection String

1. Di Storage Account → Menu kiri → **"Access keys"**
2. Klik **"Show"** pada key1
3. Copy **Connection string** (yang panjang, dimulai dengan `DefaultEndpointsProtocol=https;...`)

### Simpan:
```
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=autoclipperstore;AccountKey=XXXXX;EndpointSuffix=core.windows.net
AZURE_STORAGE_CONTAINER_RAW=raw-videos
AZURE_STORAGE_CONTAINER_CLIPS=processed-clips
AZURE_STORAGE_CONTAINER_THUMBNAILS=thumbnails
```

### Estimasi Biaya (dari $100 credit):
- Storage: ~$0.02/GB/bulan
- 100 video × 50MB = 5GB = **~$0.10/bulan**
- $100 credit bertahan **80+ bulan** dengan usage normal!

---

## STEP 5: Setup Sentry (Error Monitoring — GRATIS)

**Waktu: ~3 menit**

Sentry menangkap error di production agar kamu tahu kalau ada bug.

### Langkah-langkah:

1. Buka [sentry.io](https://sentry.io) → **Sign up with GitHub**
   - GitHub Student Pack memberi akses ke **Sentry free plan** yang lebih generous

2. **Create Organization** (jika diminta):
   - Organization name: `autoclipperpro`

3. **Create Project:**
   - Klik **"Create Project"**
   - Platform: **Python** → **FastAPI**
   - Project name: `autoclipperpro-backend`
   - Klik **"Create Project"**

4. **Copy DSN:**
   - Setelah project dibuat, akan muncul setup page
   - Cari kode: `sentry_sdk.init(dsn="https://xxxxxx@sentry.io/xxxxx")`
   - Copy bagian **DSN** saja: `https://xxxxxx@sentry.io/xxxxx`

### Simpan:
```
SENTRY_DSN=https://your-key@sentry.io/your-project-id
```

---

## STEP 6: Setup Telegram Bot (Notifikasi — GRATIS)

**Waktu: ~3 menit**

Bot Telegram mengirim notifikasi ketika video selesai diproses.

### 6a. Buat Bot

1. Buka **Telegram** → search **@BotFather**
2. Kirim: `/newbot`
3. Nama bot: `AutoClipperPro Bot`
4. Username bot: `autoclipperpro_bot` (harus unique, akhiri dengan `_bot`)
5. BotFather akan kasih **token** seperti: `7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxx`
6. **Copy token ini!**

### 6b. Dapatkan Chat ID Kamu

1. Buka bot kamu di Telegram → kirim pesan apa saja (misal: "hello")
2. Buka browser, akses URL ini (ganti TOKEN dengan token bot kamu):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
   Contoh:
   ```
   https://api.telegram.org/bot7123456789:AAHxxxxxxxxx/getUpdates
   ```
3. Di response JSON, cari:
   ```json
   "chat": {
     "id": 123456789,
     ...
   }
   ```
4. Angka `123456789` itu adalah **chat_id** kamu

### 6c. Test Bot

Buka URL ini di browser (ganti TOKEN dan CHAT_ID):
```
https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=AutoClipperPro%20connected!
```
Kalau kamu dapat pesan di Telegram → berhasil! ✅

### Simpan:
```
TELEGRAM_BOT_TOKEN=7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=123456789
```

---

## STEP 7: Deploy Backend ke Heroku (API Server)

**Waktu: ~15-20 menit**

Heroku akan menjalankan **Backend API** kamu (FastAPI server). Ini adalah "otak" dari sistem yang menerima request dari frontend.

---

### 7a. Activate Heroku Student Pack

1. Buka [heroku.com/students](https://www.heroku.com/students)
2. Klik **"Get the student offer"**
3. Login/daftar Heroku (bisa pakai email biasa)
4. Verify dengan **GitHub Student Pack** — klik "Connect GitHub"
5. Setelah verified, kamu dapat **$13/bulan credit selama 24 bulan** ($312 total!)

> ✅ Cek credit kamu di: Heroku Dashboard → **Account Settings** → **Billing** → harus terlihat "$13.00 platform credits"

---

### 7b. Install Heroku CLI (Command Line Tool)

Heroku CLI = tool untuk kontrol Heroku dari terminal/command prompt kamu.

**Untuk Windows:**

1. Buka: [devcenter.heroku.com/articles/heroku-cli](https://devcenter.heroku.com/articles/heroku-cli)
2. Klik **"Download the installer"** untuk Windows (64-bit)
3. Jalankan installer → **Next** → **Next** → **Install** → **Finish**
4. **Tutup dan buka ulang terminal/PowerShell** (penting! supaya path ke-update)
5. Verifikasi berhasil:
   ```powershell
   heroku --version
   ```
   **Output yang diharapkan:**
   ```
   heroku/8.x.x win32-x64 node-v18.x.x
   ```
   Kalau muncul "heroku is not recognized" → restart terminal atau restart PC.

---

### 7c. Install Git (Kalau Belum Punya)

Git dibutuhkan untuk push code ke Heroku. Cek dulu:

```powershell
git --version
```

**Kalau sudah muncul** `git version 2.x.x` → skip ke Step 7d.

**Kalau belum:**
1. Download dari [git-scm.com/download/win](https://git-scm.com/download/win)
2. Install → pilih semua default → **Finish**
3. Tutup dan buka ulang terminal
4. Verifikasi: `git --version`

---

### 7d. Siapkan Git Repository

Buka terminal/PowerShell, masuk ke folder project:

```powershell
# STEP 1: Masuk ke folder project
cd "r:\All Projek Saya\Sistem Clipper Otomatis"
```

**Cek apakah sudah ada git:**
```powershell
git status
```

**Kalau muncul `fatal: not a git repository`** → jalankan ini:
```powershell
# STEP 2: Inisialisasi Git (hanya sekali)
git init

# STEP 3: Set identitas Git (ganti dengan data kamu)
git config user.name "Nama Kamu"
git config user.email "emailkamu@gmail.com"
```

**Kalau sudah ada git** → langsung ke step berikutnya.

Sekarang commit semua file:
```powershell
# STEP 4: Tambahkan semua file ke Git
git add .

# STEP 5: Commit pertama
git commit -m "feat: initial commit - AutoClipperPro"
```

**Output yang diharapkan:**
```
[main (root-commit) abc1234] feat: initial commit - AutoClipperPro
 XX files changed, XXXX insertions(+)
 create mode 100644 backend/...
 ...
```

---

### 7e. Login Heroku dari Terminal

```powershell
# STEP 6: Login ke Heroku (ini akan buka browser)
heroku login
```

**Apa yang terjadi:**
1. Terminal menampilkan: `Press any key to open up the browser to login or q to exit:`
2. Tekan **Enter**
3. Browser terbuka → halaman login Heroku
4. Klik **"Log In"**
5. Browser menampilkan: "Logged in" ✅
6. Kembali ke terminal → akan muncul: `Logged in as emailkamu@gmail.com`

---

### 7f. Buat Heroku App

```powershell
# STEP 7: Buat app baru di Heroku
heroku create autoclipperpro-api
```

**Output yang diharapkan:**
```
Creating ⬢ autoclipperpro-api... done
https://autoclipperpro-api-xxxx.herokuapp.com/ | https://git.heroku.com/autoclipperpro-api.git
```

> ⚠️ Kalau nama `autoclipperpro-api` sudah diambil orang lain, ganti dengan nama unik, misal: `autoclipperpro-api-123`

```powershell
# STEP 8: Set deployment method ke Docker (container)
heroku stack:set container --app autoclipperpro-api
```

**Output yang diharapkan:**
```
Setting stack to container... done
```

---

### 7g. Set SEMUA Environment Variables

Ini bagian penting! Jalankan **satu per satu** di terminal.

> ⚠️ **GANTI semua value `"..."` dengan value milik kamu** yang sudah kamu dapatkan dari Step 1-6!

```powershell
# ==========================================
# STEP 9: Set ENV VARS — jalankan SATU PER SATU
# GANTI semua value di bawah dengan milik kamu!
# ==========================================

# --- Database (value dari Step 2) ---
heroku config:set MONGODB_URL="mongodb+srv://clipper_admin:PASSWORD@cluster0.xxxxx.mongodb.net/autoclipperpro?retryWrites=true&w=majority" --app autoclipperpro-api
```

Tunggu sampai muncul:
```
Setting MONGODB_URL and restarting ⬢ autoclipperpro-api... done
```

Lanjut:
```powershell
heroku config:set MONGODB_DB_NAME="autoclipperpro" --app autoclipperpro-api
```

```powershell
# --- Redis (value dari Step 3) ---
heroku config:set REDIS_URL="rediss://default:PASSWORD@endpoint.upstash.io:6379" --app autoclipperpro-api
```

```powershell
heroku config:set CELERY_BROKER_URL="rediss://default:PASSWORD@endpoint.upstash.io:6379/0" --app autoclipperpro-api
```

```powershell
heroku config:set CELERY_RESULT_BACKEND="rediss://default:PASSWORD@endpoint.upstash.io:6379/1" --app autoclipperpro-api
```

```powershell
# --- Storage (value dari Step 4) ---
heroku config:set AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=xxx;AccountKey=xxx;EndpointSuffix=core.windows.net" --app autoclipperpro-api
```

```powershell
# --- AI Gemini (value dari Step 1) ---
heroku config:set GEMINI_API_KEY="AIzaSyBxxx" --app autoclipperpro-api
```

```powershell
heroku config:set GEMINI_MODEL="gemini-2.5-pro-preview-05-06" --app autoclipperpro-api
```

```powershell
heroku config:set WHISPER_MODEL_SIZE="base" --app autoclipperpro-api
```

```powershell
# --- Monitoring (value dari Step 5) ---
heroku config:set SENTRY_DSN="https://xxx@sentry.io/xxx" --app autoclipperpro-api
```

```powershell
# --- Telegram (value dari Step 6) ---
heroku config:set TELEGRAM_BOT_TOKEN="7123456789:AAHxxx" --app autoclipperpro-api
```

```powershell
heroku config:set TELEGRAM_CHAT_ID="123456789" --app autoclipperpro-api
```

```powershell
# --- App Config (jangan diubah) ---
heroku config:set APP_ENV="production" --app autoclipperpro-api
heroku config:set DEBUG="false" --app autoclipperpro-api
heroku config:set SECRET_KEY="ganti-dengan-random-string-panjang-123" --app autoclipperpro-api
```

**STEP 10: Verifikasi semua env vars sudah benar:**
```powershell
heroku config --app autoclipperpro-api
```

Akan muncul semua variable. **Pastikan semua terisi**, tidak ada yang kosong atau masih bertuliskan "PASSWORD" atau "xxx".

---

### 7h. DEPLOY! (Push Code ke Heroku)

Ini step yang paling penting — push code ke Heroku dan mulai build!

```powershell
# STEP 11: Hubungkan Git dengan Heroku
heroku git:remote -a autoclipperpro-api
```

**Output yang diharapkan:**
```
set git remote heroku to https://git.heroku.com/autoclipperpro-api.git
```

```powershell
# STEP 12: Push code ke Heroku! 🚀
git push heroku main
```

> ⚠️ Kalau branch kamu namanya `master` (bukan `main`), jalankan: `git push heroku master`

**Apa yang terjadi:**
1. Heroku mengupload code kamu
2. Heroku membaca `heroku.yml` → menggunakan `Dockerfile` untuk build
3. Build Docker image (download Python, FFmpeg, pip install, dll)
4. Deploy container
5. **Proses ini butuh 5-15 menit pertama kali!** Sabar ya 😄

**Output yang sukses (di akhir):**
```
remote: Verifying deploy... done.
To https://git.heroku.com/autoclipperpro-api.git
   abc1234..def5678  main -> main
```

Kalau muncul `Verifying deploy... done` → **BERHASIL!** 🎉

---

### 7i. Verifikasi Backend Sudah Live

```powershell
# STEP 13: Buka app di browser
heroku open --app autoclipperpro-api
```

Atau buka manual di browser:
```
https://autoclipperpro-api-xxxx.herokuapp.com/health
```

**Yang diharapkan:** JSON response seperti:
```json
{"status": "healthy"}
```

**Kalau error**, cek log:
```powershell
# STEP 14: Lihat log real-time (Ctrl+C untuk berhenti)
heroku logs --tail --app autoclipperpro-api
```

### Troubleshooting Step 7:

| Problem | Kemungkinan Penyebab | Solusi |
|---------|---------------------|--------|
| `heroku is not recognized` | CLI belum terinstall | Install ulang CLI, restart terminal |
| `fatal: not a git repository` | Belum git init | Jalankan `git init` di folder project |
| `! [rejected] main -> main` | Remote sudah ada code | Jalankan: `git push heroku main --force` |
| `No default language detected` | Heroku bingung mau pakai apa | Pastikan `heroku.yml` ada di ROOT folder |
| Build error `pip install failed` | Dependency conflict | Cek `requirements.txt`, pastikan tidak ada typo |
| `Error R14 (Memory quota exceeded)` | App kehabisan RAM | Hapus dependency yang tidak perlu |
| `Application Error` di browser | App crash saat start | Cek `heroku logs --tail` untuk error detail |
| Env var tidak terbaca | Salah format | Cek `heroku config` — value tidak boleh pakai single quote |

---

## STEP 8: Deploy Worker ke Koyeb (Celery Worker)

**Waktu: ~10 menit**

Worker menjalankan tugas berat: download video, transcribe, analyze, edit, dan render.

### 8a. Buat Akun Koyeb

1. Buka [app.koyeb.com](https://app.koyeb.com) → **Sign up with GitHub**
2. Pilih plan: **Hobby Free** (tidak perlu credit card!)

### 8b. Connect GitHub Repository

1. Di Koyeb Dashboard, klik **"Create App"**
2. Deployment method: **GitHub**
3. Install Koyeb GitHub App → pilih repository kamu
4. Repository: `Sistem-Clipper-Otomatis` (atau nama repo kamu)
5. Branch: `main`

### 8c. Configure Build

1. **Builder**: **Dockerfile**
2. **Dockerfile path**: `Dockerfile.worker` (⚠️ penting! bukan `Dockerfile`)
3. **Service type**: Klik tab **"Worker"** (bukan "Web Service"!)

### 8d. Set Instance

1. Instance type: **Nano** → **Free!**
   - 0.1 vCPU
   - 512MB RAM
   - ⚠️ RAM terbatas, Whisper model harus pakai `tiny` atau `base`
2. Region: **Singapore** (sgp1)

### 8e. Set Environment Variables

Klik **"Environment Variables"** → Tambahkan semua:

| Variable | Value |
|----------|-------|
| `MONGODB_URL` | (sama seperti Step 7d) |
| `MONGODB_DB_NAME` | `autoclipperpro` |
| `CELERY_BROKER_URL` | (sama seperti Step 7d) |
| `CELERY_RESULT_BACKEND` | (sama seperti Step 7d) |
| `AZURE_STORAGE_CONNECTION_STRING` | (sama seperti Step 7d) |
| `GEMINI_API_KEY` | (sama seperti Step 7d) |
| `GEMINI_MODEL` | `gemini-2.0-flash` |
| `WHISPER_MODEL_SIZE` | `tiny` (⚠️ pakai `tiny` untuk 512MB RAM!) |
| `SENTRY_DSN` | (sama seperti Step 7d) |
| `TELEGRAM_BOT_TOKEN` | (sama seperti Step 7d) |
| `TELEGRAM_CHAT_ID` | (sama seperti Step 7d) |
| `APP_ENV` | `production` |

### 8f. Deploy

1. Klik **"Deploy"**
2. Tunggu build selesai (5-10 menit pertama kali)
3. Status harus berubah ke **"Healthy"** ✅

### Troubleshooting:
- **OOMKilled (Out of Memory)** → Ganti `WHISPER_MODEL_SIZE` ke `tiny`
- **Build gagal** → Cek apakah `Dockerfile.worker` sudah ada dan path benar
- **Worker tidak connect ke Redis** → Cek URL Redis pakai `rediss://` (bukan `redis://`)

---

## STEP 9: Deploy Frontend ke Vercel (Dashboard)

**Waktu: ~5 menit**

### 9a. Import Repository

1. Buka [vercel.com](https://vercel.com) → **Sign up with GitHub**
2. Klik **"Add New..."** → **"Project"**
3. Pilih repository: `Sistem-Clipper-Otomatis`
4. **Root Directory**: Klik **"Edit"** → ketik `frontend` → **"Continue"**
5. Framework Preset: **Next.js** (auto-detected)

### 9b. Set Environment Variables

Di halaman deploy, expand **"Environment Variables"** dan tambahkan:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://autoclipperpro-api.herokuapp.com/api/v1` |
| `NEXT_PUBLIC_WS_URL` | `wss://autoclipperpro-api.herokuapp.com/api/v1/ws` |

⚠️ Ganti `autoclipperpro-api` dengan nama Heroku app kamu yang sebenarnya.

### 9c. Deploy

1. Klik **"Deploy"**
2. Tunggu ~2 menit → Vercel akan build dan deploy
3. Kamu akan dapat URL seperti: `https://autoclipperpro.vercel.app`

### 9d. Update CORS di Heroku

Setelah dapat URL Vercel, update CORS di backend:
```bash
heroku config:set CORS_ORIGINS='["https://autoclipperpro-xxx.vercel.app"]' --app autoclipperpro-api
```
Ganti URL dengan URL Vercel kamu yang sebenarnya.

### 9e. Verifikasi

1. Buka URL Vercel kamu di browser
2. Dashboard harus muncul dengan sidebar ✅
3. Coba klik "Submit URL" → form harus muncul ✅

---

## STEP 10: Setup GitHub Actions CI/CD

**Waktu: ~3 menit**

### 10a. Tambah GitHub Secrets

1. Buka GitHub repository kamu
2. **Settings** → **Secrets and variables** → **Actions**
3. Klik **"New repository secret"** dan tambahkan:

| Secret Name | Value | Dari mana |
|-------------|-------|-----------|
| `HEROKU_API_KEY` | API key Heroku | Heroku Dashboard → Account Settings → API Key |
| `HEROKU_APP_NAME` | `autoclipperpro-api` | Nama app Heroku kamu |
| `VERCEL_TOKEN` | Token Vercel | Vercel → Settings → Tokens → Create |

### 10b. Cara Dapat Heroku API Key:
1. Login ke [dashboard.heroku.com](https://dashboard.heroku.com)
2. Klik foto profil → **"Account Settings"**
3. Scroll ke **"API Key"** → **"Reveal"**
4. Copy key tersebut

### 10c. Cara Dapat Vercel Token:
1. Login ke [vercel.com](https://vercel.com)
2. Klik foto profil → **"Settings"**
3. Menu kiri → **"Tokens"**
4. Klik **"Create"** → nama: `github-actions` → scope: Full Account
5. Copy token

### Setelah Ini:
- Setiap push ke `main` → auto-deploy ke Heroku & Vercel!
- Setiap PR → auto-run lint & build check!

---

## STEP 11: End-to-End Test 🎯

### 11a. Test Backend

```bash
# Health check
curl https://autoclipperpro-api.herokuapp.com/health

# Expected:
# {"status":"healthy","database":"connected","redis":"connected"}
```

### 11b. Test Frontend

1. Buka URL Vercel kamu (misal: `https://autoclipperpro.vercel.app`)
2. Klik **"Submit URL"** di sidebar
3. Paste URL video YouTube pendek (misal 2-3 menit)
4. Klik **"Start Processing"**

### 11c. Monitor Progress

1. Setelah submit, kamu akan diarahkan ke halaman **Job Detail**
2. Progress bar harus bergerak:
   - ⬇️ **Download** (30-60 detik)
   - 🎙️ **Transcribe** (30-120 detik, tergantung durasi)
   - 🤖 **Analyze** (10-30 detik, Gemini API)
   - ✂️ **Edit** (30-60 detik per clip)
   - 🎬 **Render** (30-60 detik per clip)
3. Setelah selesai → notifikasi Telegram masuk! 📱

### 11d. Review Clips

1. Buka **"Clips"** di sidebar
2. Clip-clip yang dihasilkan akan muncul dengan:
   - Score (0-10)
   - Hook text
   - Preview video player
3. Klik clip → **Approve** atau **Reject**
4. Download clip yang diapprove

---

## 🔍 Troubleshooting Umum

### Backend Heroku
| Problem | Solusi |
|---------|--------|
| App crash saat start | `heroku logs --tail` → cek error |
| "Application Error" di browser | Env vars belum lengkap → `heroku config` |
| Sleep setelah 30 menit idle | Normal untuk Eco dyno. Pakai [UptimeRobot](https://uptimerobot.com) (free) untuk ping tiap 5 menit |

### Worker Koyeb
| Problem | Solusi |
|---------|--------|
| OOMKilled | Ganti `WHISPER_MODEL_SIZE=tiny` |
| Worker tidak jalan | Cek logs di Koyeb Dashboard |
| Task stuck "pending" | Worker tidak connect ke Redis — cek URL |

### Frontend Vercel
| Problem | Solusi |
|---------|--------|
| "Failed to load" errors | Cek `NEXT_PUBLIC_API_URL` benar |
| CORS error | Update `CORS_ORIGINS` di Heroku config |
| WebSocket tidak connect | Pastikan URL pakai `wss://` (bukan `ws://`) |

### Redis Upstash
| Problem | Solusi |
|---------|--------|
| "Connection refused" | URL harus pakai `rediss://` (double s = TLS) |
| "Command limit reached" | Naikkan Celery polling interval di config |

---

## 📝 Checklist Ringkas

Setelah selesai semua step, pastikan kamu punya 12 value ini:

```bash
# ✅ Checklist — semua harus terisi
GEMINI_API_KEY=          # Step 1
MONGODB_URL=             # Step 2
MONGODB_DB_NAME=         # Step 2
REDIS_URL=               # Step 3
CELERY_BROKER_URL=       # Step 3
CELERY_RESULT_BACKEND=   # Step 3
AZURE_STORAGE_CONNECTION_STRING=  # Step 4
SENTRY_DSN=              # Step 5
TELEGRAM_BOT_TOKEN=      # Step 6
TELEGRAM_CHAT_ID=        # Step 6
HEROKU_APP_URL=          # Step 7
VERCEL_APP_URL=          # Step 9
```

**Selamat! AutoClipperPro sudah live di production! 🎉**
