"""
SocialAccount Document Model (Beanie ODM)
==========================================
Menyimpan OAuth tokens untuk koneksi platform sosial media per user.
Access token dienkripsi sebelum disimpan.
"""

from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import Field
from bson import PydanticObjectId


class SocialAccount(Document):
    """Connected social media account (OAuth token store)."""

    user_id: PydanticObjectId
    platform: str                     # "tiktok" | "instagram" | "youtube"
    platform_user_id: str             # UID dari platform
    platform_username: str            # @username / display name
    platform_avatar: Optional[str] = None

    # Tokens (disimpan as-is; enkripsi di layer service jika perlu)
    access_token: str
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None

    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "social_accounts"
        indexes = [
            "user_id",
            [("user_id", 1), ("platform", 1)],  # compound: 1 account per platform per user
        ]
