"""
Shared Test Fixtures
======================
Provides in-memory MongoDB (via mongomock-motor + Beanie),
FastAPI test client, and helper fixtures for users and auth tokens.

Usage:
    - `test_client`   — AsyncClient against the FastAPI app
    - `mock_db`       — in-memory MongoDB database
    - `test_user`     — a regular (non-admin) User document
    - `auth_headers`  — {"Authorization": "Bearer <token>"} for test_user
    - `admin_user`    — an admin User document
    - `admin_headers` — {"Authorization": "Bearer <token>"} for admin_user
"""

import os

import pytest
import pytest_asyncio
import mongomock_motor
from beanie import init_beanie
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

# --- Override settings BEFORE importing the app ---
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-chars!!")
os.environ.setdefault("SENTRY_DSN", "")

from app.models.user import User          # noqa: E402
from app.models.video import Video        # noqa: E402
from app.models.job import Job            # noqa: E402
from app.models.clip import Clip          # noqa: E402
from app.models.transcript import Transcript  # noqa: E402
from app.models.style import CaptionStyle # noqa: E402
from app.services.auth_service import create_access_token, hash_password  # noqa: E402

_ALL_MODELS = [User, Video, Job, Clip, Transcript, CaptionStyle]


@pytest_asyncio.fixture()
async def mock_db():
    """
    Initialize Beanie with an in-memory MongoDB (mongomock-motor).
    Each test function gets a fresh database.
    """
    client = mongomock_motor.AsyncMongoMockClient()
    db = client["test_clipper_db"]
    await init_beanie(database=db, document_models=_ALL_MODELS)
    yield db


@pytest_asyncio.fixture()
async def test_client(mock_db):
    """
    FastAPI AsyncClient with mocked database.
    `init_database` is patched so the lifespan does not attempt a real
    MongoDB connection; Beanie is already initialised by `mock_db`.
    """
    with patch("app.database.init_database", new=AsyncMock()):
        from app.main import app  # import here so env vars are already set
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client


# ------------------------------------------------------------------ Users

@pytest_asyncio.fixture()
async def test_user(mock_db) -> User:
    """Regular (non-admin) user saved to the mock database."""
    user = User(
        email="user@test.com",
        hashed_password=hash_password("Password123!"),
        full_name="Test User",
        is_active=True,
        is_admin=False,
    )
    await user.insert()
    return user


@pytest_asyncio.fixture()
async def admin_user(mock_db) -> User:
    """Admin user saved to the mock database."""
    user = User(
        email="admin@test.com",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Admin User",
        is_active=True,
        is_admin=True,
    )
    await user.insert()
    return user


# ------------------------------------------------------------------ Auth headers

@pytest_asyncio.fixture()
async def auth_headers(test_user) -> dict:
    """Bearer token Authorization header for the regular test user."""
    token = create_access_token(
        user_id=str(test_user.id),
        email=test_user.email,
        is_admin=False,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture()
async def admin_headers(admin_user) -> dict:
    """Bearer token Authorization header for the admin user."""
    token = create_access_token(
        user_id=str(admin_user.id),
        email=admin_user.email,
        is_admin=True,
    )
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------------ Sample documents

@pytest_asyncio.fixture()
async def sample_video(mock_db, test_user) -> Video:
    """A Video document owned by test_user."""
    video = Video(
        original_filename="sample.mp4",
        source_type="url",
        source_url="https://www.youtube.com/watch?v=test123",
        source_platform="youtube",
        status="downloaded",
        user_id=str(test_user.id),
    )
    await video.insert()
    return video


@pytest_asyncio.fixture()
async def sample_job(mock_db, test_user, sample_video) -> Job:
    """A Job document owned by test_user."""
    job = Job(
        video_id=str(sample_video.id),
        user_id=str(test_user.id),
        status="queued",
    )
    await job.insert()
    return job


@pytest_asyncio.fixture()
async def sample_clip(mock_db, test_user, sample_video, sample_job) -> Clip:
    """A Clip document owned by test_user."""
    clip = Clip(
        video_id=str(sample_video.id),
        job_id=str(sample_job.id),
        user_id=str(test_user.id),
        start_time=10.0,
        end_time=40.0,
        duration=30.0,
        highlight_score=8.5,
        status="completed",
    )
    await clip.insert()
    return clip
