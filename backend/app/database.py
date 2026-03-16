"""
MongoDB Database Connection
=============================
Async MongoDB connection using Motor + Beanie ODM.
Supports both local MongoDB and MongoDB Atlas.
"""

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

# MongoDB client instance (lazy-initialized)
_client: AsyncIOMotorClient | None = None


async def init_database():
    """
    Initialize MongoDB connection and Beanie ODM.
    Called during FastAPI startup event.
    """
    global _client

    # Import all document models for Beanie
    from app.models.video import Video
    from app.models.job import Job
    from app.models.clip import Clip
    from app.models.transcript import Transcript
    from app.models.style import CaptionStyle
    from app.models.user import User
    from app.models.social_account import SocialAccount
    from app.models.publish_job import PublishJob

    _client = AsyncIOMotorClient(settings.MONGODB_URL)
    database = _client[settings.MONGODB_DB_NAME]

    await init_beanie(
        database=database,
        document_models=[
            Video,
            Job,
            Clip,
            Transcript,
            CaptionStyle,
            User,
            SocialAccount,
            PublishJob,
        ],
    )

    print(f"✅ Connected to MongoDB: {settings.MONGODB_DB_NAME}")


async def close_database():
    """Close MongoDB connection. Called during FastAPI shutdown."""
    global _client
    if _client:
        _client.close()
        print("🔌 MongoDB connection closed.")


def get_database():
    """Get the database instance for direct queries."""
    if _client is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _client[settings.MONGODB_DB_NAME]
