"""
Social Media Publisher Service
================================
Handles OAuth connections and video publishing to:
  - TikTok (Content Posting API v2)
  - Instagram (Graph API — Reels)
  - YouTube (Data API v3 — Shorts)

OAuth Flow per platform:
  1. Frontend hits GET /publish/connect/{platform} → redirect URL
  2. User authorizes on platform → callback to GET /publish/callback/{platform}
  3. Tokens saved in SocialAccount collection
  4. Frontend calls POST /publish/{clip_id} with platform choice
"""

import httpx
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional

from app.config import settings
from app.models.social_account import SocialAccount
from app.models.publish_job import PublishJob
from app.models.clip import Clip
from bson import PydanticObjectId


# ---------------------------------------------------------------------------
# OAuth: Get authorization URL
# ---------------------------------------------------------------------------

def get_oauth_url(platform: str, user_id: str) -> str:
    """Return the OAuth authorization URL for a given platform."""
    state = f"{user_id}:{platform}"  # simple state; use CSRF token in production

    if platform == "tiktok":
        params = urllib.parse.urlencode({
            "client_key": settings.TIKTOK_CLIENT_KEY,
            "scope": "video.upload,user.info.basic",
            "response_type": "code",
            "redirect_uri": settings.TIKTOK_REDIRECT_URI,
            "state": state,
        })
        return f"https://www.tiktok.com/v2/auth/authorize/?{params}"

    elif platform == "instagram":
        params = urllib.parse.urlencode({
            "client_id": settings.INSTAGRAM_APP_ID,
            "redirect_uri": settings.INSTAGRAM_REDIRECT_URI,
            "scope": "instagram_basic,instagram_content_publish",
            "response_type": "code",
            "state": state,
        })
        return f"https://api.instagram.com/oauth/authorize?{params}"

    elif platform == "youtube":
        params = urllib.parse.urlencode({
            "client_id": settings.YOUTUBE_CLIENT_ID,
            "redirect_uri": settings.YOUTUBE_REDIRECT_URI,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/youtube.upload",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        })
        return f"https://accounts.google.com/o/oauth2/v2/auth?{params}"

    raise ValueError(f"Unknown platform: {platform}")


# ---------------------------------------------------------------------------
# OAuth: Exchange code for tokens + save SocialAccount
# ---------------------------------------------------------------------------

async def connect_platform(platform: str, code: str, user_id: str) -> SocialAccount:
    """Exchange OAuth code for tokens and save/update SocialAccount."""

    if platform == "tiktok":
        return await _connect_tiktok(code, user_id)
    elif platform == "instagram":
        return await _connect_instagram(code, user_id)
    elif platform == "youtube":
        return await _connect_youtube(code, user_id)
    raise ValueError(f"Unknown platform: {platform}")


async def _connect_tiktok(code: str, user_id: str) -> SocialAccount:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://open.tiktokapis.com/v2/oauth/token/",
            data={
                "client_key": settings.TIKTOK_CLIENT_KEY,
                "client_secret": settings.TIKTOK_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.TIKTOK_REDIRECT_URI,
            },
        )
        r.raise_for_status()
        token_data = r.json()

    access_token = token_data["access_token"]
    open_id = token_data["open_id"]
    expires_in = token_data.get("expires_in", 86400)

    # Fetch user info
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://open.tiktokapis.com/v2/user/info/",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"fields": "display_name,avatar_url"},
        )
        user_data = r.json().get("data", {}).get("user", {})

    return await _upsert_social_account(
        user_id=user_id,
        platform="tiktok",
        platform_user_id=open_id,
        platform_username=user_data.get("display_name", "TikTok User"),
        platform_avatar=user_data.get("avatar_url"),
        access_token=access_token,
        refresh_token=token_data.get("refresh_token"),
        expires_in=expires_in,
    )


async def _connect_instagram(code: str, user_id: str) -> SocialAccount:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.instagram.com/oauth/access_token",
            data={
                "client_id": settings.INSTAGRAM_APP_ID,
                "client_secret": settings.INSTAGRAM_APP_SECRET,
                "grant_type": "authorization_code",
                "redirect_uri": settings.INSTAGRAM_REDIRECT_URI,
                "code": code,
            },
        )
        r.raise_for_status()
        token_data = r.json()

    short_token = token_data["access_token"]
    ig_user_id = str(token_data["user_id"])

    # Exchange for long-lived token
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://graph.instagram.com/access_token",
            params={
                "grant_type": "ig_exchange_token",
                "client_secret": settings.INSTAGRAM_APP_SECRET,
                "access_token": short_token,
            },
        )
        long_data = r.json()

    long_token = long_data.get("access_token", short_token)
    expires_in = long_data.get("expires_in", 5183944)  # ~60 days

    # Fetch username
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://graph.instagram.com/{ig_user_id}",
            params={"fields": "username,profile_picture_url", "access_token": long_token},
        )
        profile = r.json()

    return await _upsert_social_account(
        user_id=user_id,
        platform="instagram",
        platform_user_id=ig_user_id,
        platform_username=profile.get("username", "Instagram User"),
        platform_avatar=profile.get("profile_picture_url"),
        access_token=long_token,
        expires_in=expires_in,
    )


async def _connect_youtube(code: str, user_id: str) -> SocialAccount:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.YOUTUBE_CLIENT_ID,
                "client_secret": settings.YOUTUBE_CLIENT_SECRET,
                "redirect_uri": settings.YOUTUBE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        r.raise_for_status()
        token_data = r.json()

    access_token = token_data["access_token"]

    # Fetch channel info
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://www.googleapis.com/youtube/v3/channels",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"part": "snippet", "mine": "true"},
        )
        ch_data = r.json()

    channel = ch_data.get("items", [{}])[0]
    channel_id = channel.get("id", "unknown")
    channel_title = channel.get("snippet", {}).get("title", "YouTube Channel")
    avatar = channel.get("snippet", {}).get("thumbnails", {}).get("default", {}).get("url")

    return await _upsert_social_account(
        user_id=user_id,
        platform="youtube",
        platform_user_id=channel_id,
        platform_username=channel_title,
        platform_avatar=avatar,
        access_token=access_token,
        refresh_token=token_data.get("refresh_token"),
        expires_in=token_data.get("expires_in", 3600),
    )


async def _upsert_social_account(
    user_id: str,
    platform: str,
    platform_user_id: str,
    platform_username: str,
    platform_avatar: Optional[str],
    access_token: str,
    refresh_token: Optional[str] = None,
    expires_in: int = 86400,
) -> SocialAccount:
    """Create or update SocialAccount document."""
    oid = PydanticObjectId(user_id)
    existing = await SocialAccount.find_one(
        SocialAccount.user_id == oid,
        SocialAccount.platform == platform,
    )

    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    if existing:
        existing.access_token = access_token
        existing.refresh_token = refresh_token
        existing.token_expires_at = expires_at
        existing.platform_username = platform_username
        existing.platform_avatar = platform_avatar
        existing.is_active = True
        existing.updated_at = datetime.utcnow()
        await existing.save()
        return existing

    account = SocialAccount(
        user_id=oid,
        platform=platform,
        platform_user_id=platform_user_id,
        platform_username=platform_username,
        platform_avatar=platform_avatar,
        access_token=access_token,
        refresh_token=refresh_token,
        token_expires_at=expires_at,
    )
    await account.insert()
    return account


# ---------------------------------------------------------------------------
# Publish to platforms
# ---------------------------------------------------------------------------

async def publish_to_platform(
    publish_job: PublishJob,
    clip: Clip,
    video_url: str,
) -> str:
    """
    Upload video to the target platform.
    Returns the platform post URL.
    """
    account = await SocialAccount.get(publish_job.social_account_id)
    if not account:
        raise ValueError("Social account not found")

    caption_with_tags = publish_job.caption
    if publish_job.hashtags:
        tags_str = " ".join(f"#{t.lstrip('#')}" for t in publish_job.hashtags)
        caption_with_tags = f"{caption_with_tags}\n\n{tags_str}"

    if account.platform == "tiktok":
        return await _publish_tiktok(account, video_url, caption_with_tags)
    elif account.platform == "instagram":
        return await _publish_instagram(account, video_url, caption_with_tags)
    elif account.platform == "youtube":
        return await _publish_youtube(account, video_url, caption_with_tags, clip)
    raise ValueError(f"Unknown platform: {account.platform}")


async def _publish_tiktok(account: SocialAccount, video_url: str, caption: str) -> str:
    """Upload video to TikTok via Content Posting API."""
    async with httpx.AsyncClient(timeout=120) as client:
        # Init upload
        r = await client.post(
            "https://open.tiktokapis.com/v2/post/publish/video/init/",
            headers={"Authorization": f"Bearer {account.access_token}"},
            json={
                "post_info": {
                    "title": caption[:2200],
                    "privacy_level": "PUBLIC_TO_EVERYONE",
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                },
                "source_info": {
                    "source": "PULL_FROM_URL",
                    "video_url": video_url,
                },
            },
        )
        r.raise_for_status()
        data = r.json()

    publish_id = data.get("data", {}).get("publish_id", "")
    return f"https://www.tiktok.com/@{account.platform_username}/video/{publish_id}"


async def _publish_instagram(account: SocialAccount, video_url: str, caption: str) -> str:
    """Publish Reel to Instagram via Graph API."""
    ig_user_id = account.platform_user_id
    token = account.access_token

    async with httpx.AsyncClient(timeout=120) as client:
        # Step 1: Create media container
        r = await client.post(
            f"https://graph.facebook.com/v19.0/{ig_user_id}/media",
            params={
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption[:2200],
                "share_to_feed": "true",
                "access_token": token,
            },
        )
        r.raise_for_status()
        container_id = r.json()["id"]

        # Step 2: Publish container
        r2 = await client.post(
            f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish",
            params={"creation_id": container_id, "access_token": token},
        )
        r2.raise_for_status()
        media_id = r2.json()["id"]

    return f"https://www.instagram.com/p/{media_id}/"


async def _publish_youtube(
    account: SocialAccount, video_url: str, caption: str, clip: Clip
) -> str:
    """Upload Short to YouTube via Data API v3."""
    import io
    import tempfile
    import os

    token = account.access_token
    title = (clip.hook_text or "AutoClipper Short")[:100]
    description = caption[:5000]

    # Download video to temp file (YouTube requires direct upload)
    async with httpx.AsyncClient(timeout=300) as client:
        video_resp = await client.get(video_url)
        video_resp.raise_for_status()
        video_bytes = video_resp.content

    # Upload using resumable upload
    async with httpx.AsyncClient(timeout=300) as client:
        # Init resumable upload
        r = await client.post(
            "https://www.googleapis.com/upload/youtube/v3/videos",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Upload-Content-Type": "video/*",
                "X-Upload-Content-Length": str(len(video_bytes)),
            },
            params={"uploadType": "resumable", "part": "snippet,status"},
            json={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": clip.hashtags or [],
                    "categoryId": "22",  # People & Blogs
                },
                "status": {"privacyStatus": "public"},
            },
        )
        r.raise_for_status()
        upload_url = r.headers["Location"]

        # Upload bytes
        r2 = await client.put(
            upload_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "video/*",
            },
            content=video_bytes,
        )
        r2.raise_for_status()
        video_id = r2.json()["id"]

    return f"https://www.youtube.com/shorts/{video_id}"
