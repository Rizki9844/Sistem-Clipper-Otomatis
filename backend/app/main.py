"""
FastAPI Application Entry Point
=================================
Main application with CORS, Sentry, structured logging,
lifecycle hooks, and global exception handling.
"""

import traceback
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import init_database, close_database
from app.logging_config import setup_logging, get_logger
from app.exceptions import ClipperBaseError
from app.api.rate_limit import limiter

# ---- Initialize logging first ----
setup_logging()
logger = get_logger("app")

# ---- Sentry Initialization ----
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.2 if settings.is_production else 1.0,
        profiles_sample_rate=0.1,
        environment=settings.APP_ENV,
    )


# ---- Application Lifecycle ----
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events — fault tolerant."""
    logger.info("Starting application", app=settings.APP_NAME, env=settings.APP_ENV)

    # Try to connect to MongoDB, but don't crash if it fails
    try:
        await init_database()
        logger.info("Database connected successfully")

        # Create default caption style if none exists
        await _ensure_default_style()
    except Exception as e:
        logger.error(
            "Database connection failed at startup — app will run in degraded mode",
            error=str(e),
            traceback=traceback.format_exc(),
        )
        # Print to stdout so it shows in Heroku logs
        print(f"⚠️ DATABASE CONNECTION FAILED: {e}")
        print(traceback.format_exc())

    yield

    try:
        await close_database()
    except Exception:
        pass
    logger.info("Application shut down")


async def _ensure_default_style():
    """Create the default Hormozi-style caption template if it doesn't exist."""
    from app.models.style import CaptionStyle
    existing = await CaptionStyle.find_one(CaptionStyle.is_default == True)
    if not existing:
        default_style = CaptionStyle(
            name="Hormozi Bold",
            description="Bold white text with gold word-by-word highlight. Alex Hormozi signature style.",
            is_default=True,
        )
        await default_style.insert()
        logger.info("Created default caption style", name="Hormozi Bold")


# ---- FastAPI App ----
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "🎬 Enterprise Automated Video Clipper & Editing System\n\n"
        "Submit a video URL → AI analyzes for highlights → "
        "Auto-generates short clips with Hormozi-style captions → "
        "Notifies you via WhatsApp/Telegram when done."
    ),
    version="0.2.0",
    lifespan=lifespan,
    # Always enable docs (helpful for debugging & API testing)
    docs_url="/docs",
    redoc_url="/redoc",
)

# Attach limiter to app state (required by SlowAPI)
app.state.limiter = limiter


# ---- Global Exception Handler ----
@app.exception_handler(ClipperBaseError)
async def clipper_exception_handler(request: Request, exc: ClipperBaseError):
    """Handle all custom exceptions with structured error response."""
    logger.error("Request error", error=exc.__class__.__name__, message=exc.message,
                 details=exc.details, path=request.url.path)
    return JSONResponse(
        status_code=400,
        content=exc.to_dict(),
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Custom 429 response for rate-limited requests."""
    logger.warning("Rate limit exceeded", path=request.url.path,
                   detail=str(exc.detail))
    return JSONResponse(
        status_code=429,
        content={
            "error": "RateLimitExceeded",
            "message": f"Too many requests. {exc.detail}",
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions."""
    logger.error("Unhandled error", error=type(exc).__name__, message=str(exc),
                 path=request.url.path, exc_info=True)
    if settings.SENTRY_DSN:
        sentry_sdk.capture_exception(exc)
    return JSONResponse(
        status_code=500,
        content={"error": "InternalServerError", "message": "An unexpected error occurred."},
    )


# ---- CORS Middleware ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- API Routes ----
from app.api.router import api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")


# ---- Health Check ----
@app.get("/health", tags=["Health"])
async def health_check():
    """Deep health check with dependency status."""
    health = {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "0.2.0",
        "environment": settings.APP_ENV,
        "checks": {},
    }

    # Check MongoDB
    try:
        from app.database import get_database
        db = get_database()
        await db.command("ping")
        health["checks"]["mongodb"] = "connected"
    except Exception as e:
        health["checks"]["mongodb"] = f"error: {str(e)[:100]}"
        health["status"] = "degraded"

    # Check Redis
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL, ssl_cert_reqs=None)
        r.ping()
        health["checks"]["redis"] = "connected"
    except Exception as e:
        health["checks"]["redis"] = f"error: {str(e)[:100]}"
        health["status"] = "degraded"

    return health


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint — API info and quickstart."""
    return {
        "app": settings.APP_NAME,
        "version": "0.2.0",
        "description": "Automated Video Clipper & Editing System",
        "quickstart": {
            "submit_url": "POST /api/v1/videos/from-url",
            "upload_file": "POST /api/v1/videos/upload",
            "check_status": "GET /api/v1/jobs/{job_id}",
            "list_clips": "GET /api/v1/clips?video_id={video_id}",
            "docs": "/docs",
        },
    }
