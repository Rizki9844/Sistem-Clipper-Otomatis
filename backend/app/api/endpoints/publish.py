"""
Publish API Endpoints
======================
Social media publishing untuk clips yang sudah diapprove.

Routes:
  GET  /publish/accounts              — daftar connected social accounts
  GET  /publish/connect/{platform}    — get OAuth URL
  GET  /publish/callback/{platform}   — OAuth callback (redirect dari platform)
  DELETE /publish/accounts/{id}       — disconnect platform
  POST /publish/{clip_id}             — publish clip ke platform
  GET  /publish/jobs                  — riwayat publish jobs
  GET  /publish/jobs/{id}             — detail publish job
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.api.deps import get_current_user, require_feature
from app.models.user import User
from app.models.clip import Clip
from app.models.social_account import SocialAccount
from app.models.publish_job import PublishJob
from app.services.publisher import get_oauth_url, connect_platform
from app.services.plan_config import can_use_platform, get_plan
from bson import PydanticObjectId

router = APIRouter()

SUPPORTED_PLATFORMS = {"tiktok", "instagram", "youtube"}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PublishRequest(BaseModel):
    platform: str
    social_account_id: str
    caption: str = ""
    hashtags: list[str] = []
    scheduled_at: Optional[datetime] = None  # None = publish immediately


class PublishJobResponse(BaseModel):
    id: str
    clip_id: str
    platform: str
    status: str
    platform_post_url: Optional[str]
    scheduled_at: Optional[datetime]
    published_at: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime


# ---------------------------------------------------------------------------
# Connected accounts
# ---------------------------------------------------------------------------

@router.get("/accounts")
async def list_connected_accounts(current_user: User = Depends(get_current_user)):
    """List all connected social accounts for the current user."""
    accounts = await SocialAccount.find(
        SocialAccount.user_id == current_user.id,
        SocialAccount.is_active == True,
    ).to_list()

    return {
        "accounts": [
            {
                "id": str(a.id),
                "platform": a.platform,
                "username": a.platform_username,
                "avatar": a.platform_avatar,
                "connected_at": a.created_at,
                "token_expires_at": a.token_expires_at,
            }
            for a in accounts
        ]
    }


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
):
    """Disconnect a social account."""
    account = await SocialAccount.get(account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    account.is_active = False
    await account.save()


# ---------------------------------------------------------------------------
# OAuth connect flow
# ---------------------------------------------------------------------------

@router.get("/connect/{platform}")
async def get_connect_url(
    platform: str,
    current_user: User = Depends(require_feature("publish_platforms", "starter")),
):
    """
    Get the OAuth authorization URL for connecting a social platform.
    Frontend should redirect user to the returned URL.
    """
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Platform '{platform}' not supported")

    # Check if user's plan allows this platform
    if not can_use_platform(current_user.plan_tier, platform) and not current_user.is_admin:
        plan = get_plan(current_user.plan_tier)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "PLATFORM_NOT_ALLOWED",
                "message": f"Your {current_user.plan_tier} plan does not include {platform}. Upgrade to unlock.",
                "platform": platform,
                "current_plan": current_user.plan_tier,
            },
        )

    url = get_oauth_url(platform, str(current_user.id))
    return {"oauth_url": url, "platform": platform}


@router.get("/callback/{platform}")
async def oauth_callback(
    platform: str,
    code: str = Query(...),
    state: str = Query(""),
    request: Request = None,
):
    """
    OAuth callback. Platform redirects here after user authorizes.
    Saves tokens to DB and redirects user back to frontend.
    """
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail="Unknown platform")

    # Extract user_id from state
    user_id = state.split(":")[0] if state else None
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    try:
        await connect_platform(platform, code, user_id)
    except Exception as e:
        # Redirect to frontend with error
        return RedirectResponse(url=f"/billing?oauth_error={platform}&reason={str(e)}")

    # Update user's connected_platforms list
    user = await User.get(user_id)
    if user and platform not in user.connected_platforms:
        user.connected_platforms.append(platform)
        await user.save()

    return RedirectResponse(url=f"/clips?connected={platform}")


# ---------------------------------------------------------------------------
# Publish clip
# ---------------------------------------------------------------------------

@router.post("/{clip_id}", response_model=PublishJobResponse)
async def publish_clip(
    clip_id: str,
    body: PublishRequest,
    current_user: User = Depends(require_feature("publish_platforms", "starter")),
):
    """
    Queue a clip for publishing to a social platform.
    Dispatches to Celery worker for async upload.
    """
    # Validate platform allowed by plan
    if not can_use_platform(current_user.plan_tier, body.platform) and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "PLATFORM_NOT_ALLOWED",
                "message": f"Upgrade to access {body.platform} publishing",
                "platform": body.platform,
            },
        )

    # Validate clip ownership
    clip = await Clip.get(clip_id)
    if not clip or clip.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Clip not found")

    if clip.review_status != "approved":
        raise HTTPException(
            status_code=400,
            detail="Only approved clips can be published. Please approve the clip first.",
        )

    # Validate social account ownership
    account = await SocialAccount.get(body.social_account_id)
    if not account or account.user_id != current_user.id or not account.is_active:
        raise HTTPException(status_code=404, detail="Social account not found or disconnected")

    if account.platform != body.platform:
        raise HTTPException(
            status_code=400,
            detail=f"Account is for {account.platform}, not {body.platform}",
        )

    # Create PublishJob
    pub_job = PublishJob(
        user_id=current_user.id,
        clip_id=PydanticObjectId(clip_id),
        social_account_id=PydanticObjectId(body.social_account_id),
        platform=body.platform,
        caption=body.caption or clip.hook_text or "",
        hashtags=body.hashtags or clip.hashtags or [],
        scheduled_at=body.scheduled_at,
        status="scheduled" if body.scheduled_at else "pending",
    )
    await pub_job.insert()

    # Dispatch Celery task (unless scheduled)
    if not body.scheduled_at:
        from app.workers.tasks.publish import publish_clip_task
        publish_clip_task.delay(str(pub_job.id))

    return PublishJobResponse(
        id=str(pub_job.id),
        clip_id=clip_id,
        platform=body.platform,
        status=pub_job.status,
        platform_post_url=pub_job.platform_post_url,
        scheduled_at=pub_job.scheduled_at,
        published_at=pub_job.published_at,
        error_message=pub_job.error_message,
        created_at=pub_job.created_at,
    )


# ---------------------------------------------------------------------------
# Publish job history
# ---------------------------------------------------------------------------

@router.get("/jobs")
async def list_publish_jobs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    """List publish job history for the current user."""
    jobs = await PublishJob.find(
        PublishJob.user_id == current_user.id,
    ).sort(-PublishJob.created_at).skip(offset).limit(limit).to_list()

    return {
        "jobs": [
            {
                "id": str(j.id),
                "clip_id": str(j.clip_id),
                "platform": j.platform,
                "status": j.status,
                "platform_post_url": j.platform_post_url,
                "scheduled_at": j.scheduled_at,
                "published_at": j.published_at,
                "error_message": j.error_message,
                "created_at": j.created_at,
            }
            for j in jobs
        ],
        "total": await PublishJob.find(PublishJob.user_id == current_user.id).count(),
    }


@router.get("/jobs/{job_id}")
async def get_publish_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get detail of a specific publish job."""
    job = await PublishJob.get(job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Publish job not found")

    return {
        "id": str(job.id),
        "clip_id": str(job.clip_id),
        "platform": job.platform,
        "status": job.status,
        "caption": job.caption,
        "hashtags": job.hashtags,
        "platform_post_id": job.platform_post_id,
        "platform_post_url": job.platform_post_url,
        "scheduled_at": job.scheduled_at,
        "published_at": job.published_at,
        "error_message": job.error_message,
        "retry_count": job.retry_count,
        "created_at": job.created_at,
    }
