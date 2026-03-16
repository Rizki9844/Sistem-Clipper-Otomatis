"""
Admin API Endpoints
====================
System management endpoints — admin only.
Allows viewing/managing all users, monitoring all jobs,
and retrieving system-wide analytics.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from app.models.user import User
from app.models.video import Video
from app.models.job import Job
from app.models.clip import Clip
from app.api.deps import get_current_admin
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("api.admin")


# ---- Response Models ----

class AdminUserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    is_admin: bool
    plan_tier: str
    monthly_quota: int
    used_quota: int
    created_at: datetime
    last_login: Optional[datetime] = None
    # Stats (computed)
    total_videos: int = 0
    total_jobs: int = 0
    total_clips: int = 0


class UserUpdateRequest(BaseModel):
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    plan_tier: Optional[str] = None
    monthly_quota: Optional[int] = None


# ================================================================
# System-wide Stats
# ================================================================

@router.get("/stats")
async def admin_stats(_: User = Depends(get_current_admin)):
    """System-wide analytics dashboard for admins."""
    total_users = await User.find_all().count()
    active_users = await User.find(User.is_active == True).count()
    total_videos = await Video.find_all().count()
    total_jobs = await Job.find_all().count()
    total_clips = await Clip.find_all().count()
    jobs_processing = await Job.find(Job.status == "processing").count()
    jobs_completed = await Job.find(Job.status == "completed").count()
    jobs_failed = await Job.find(Job.status == "failed").count()
    jobs_queued = await Job.find(Job.status == "queued").count()

    # Users by plan
    free_users = await User.find(User.plan_tier == "free").count()
    pro_users = await User.find(User.plan_tier == "pro").count()

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "free_plan": free_users,
            "pro_plan": pro_users,
        },
        "videos": {"total": total_videos},
        "jobs": {
            "total": total_jobs,
            "processing": jobs_processing,
            "completed": jobs_completed,
            "failed": jobs_failed,
            "queued": jobs_queued,
        },
        "clips": {"total": total_clips},
    }


# ================================================================
# User Management
# ================================================================

@router.get("/users", response_model=list[AdminUserResponse])
async def list_all_users(
    search: Optional[str] = Query(None, description="Search by email or name"),
    is_active: Optional[bool] = Query(None),
    plan_tier: Optional[str] = Query(None, description="free or pro"),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    _: User = Depends(get_current_admin),
):
    """List all registered users with optional filtering."""
    query = {}
    if is_active is not None:
        query["is_active"] = is_active
    if plan_tier:
        query["plan_tier"] = plan_tier

    users = await User.find(query).sort("-created_at").skip(skip).limit(limit).to_list()

    # Apply text search filter (email/name) in memory — small dataset
    if search:
        s = search.lower()
        users = [u for u in users if s in u.email.lower() or s in u.full_name.lower()]

    result = []
    for u in users:
        user_id = str(u.id)
        total_videos = await Video.find(Video.user_id == user_id).count()
        total_jobs = await Job.find(Job.user_id == user_id).count()
        total_clips = await Clip.find(Clip.user_id == user_id).count()
        result.append(AdminUserResponse(
            id=user_id,
            email=u.email,
            full_name=u.full_name,
            is_active=u.is_active,
            is_admin=u.is_admin,
            plan_tier=u.plan_tier,
            monthly_quota=u.monthly_quota,
            used_quota=u.used_quota,
            created_at=u.created_at,
            last_login=u.last_login,
            total_videos=total_videos,
            total_jobs=total_jobs,
            total_clips=total_clips,
        ))

    return result


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user_detail(
    user_id: str,
    _: User = Depends(get_current_admin),
):
    """Get detailed information about a specific user."""
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    total_videos = await Video.find(Video.user_id == user_id).count()
    total_jobs = await Job.find(Job.user_id == user_id).count()
    total_clips = await Clip.find(Clip.user_id == user_id).count()

    return AdminUserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        plan_tier=user.plan_tier,
        monthly_quota=user.monthly_quota,
        used_quota=user.used_quota,
        created_at=user.created_at,
        last_login=user.last_login,
        total_videos=total_videos,
        total_jobs=total_jobs,
        total_clips=total_clips,
    )


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    data: UserUpdateRequest,
    admin: User = Depends(get_current_admin),
):
    """
    Update user attributes (activate/deactivate, promote/demote admin, change plan).
    Admins cannot demote themselves.
    """
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent admin from removing their own admin role
    if data.is_admin is False and str(user.id) == str(admin.id):
        raise HTTPException(status_code=400, detail="Cannot remove your own admin role")

    updates = {}
    if data.is_active is not None:
        updates[User.is_active] = data.is_active
    if data.is_admin is not None:
        updates[User.is_admin] = data.is_admin
    if data.plan_tier is not None:
        if data.plan_tier not in ("free", "pro"):
            raise HTTPException(status_code=400, detail="plan_tier must be 'free' or 'pro'")
        updates[User.plan_tier] = data.plan_tier
        # Pro = unlimited (0), Free = 5
        updates[User.monthly_quota] = 0 if data.plan_tier == "pro" else 5
    if data.monthly_quota is not None:
        updates[User.monthly_quota] = data.monthly_quota

    if updates:
        await user.set(updates)

    logger.info("User updated by admin", target_user=user_id, admin=str(admin.id), changes=list(updates.keys()))
    return {"message": "User updated successfully", "user_id": user_id}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: User = Depends(get_current_admin),
):
    """
    Permanently delete a user and ALL their data (videos, jobs, clips).
    This cannot be undone.
    """
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if str(user.id) == str(admin.id):
        raise HTTPException(status_code=400, detail="Cannot delete your own account via admin panel")

    # Cascade delete all user data
    await Clip.find(Clip.user_id == user_id).delete()
    await Job.find(Job.user_id == user_id).delete()
    await Video.find(Video.user_id == user_id).delete()
    await user.delete()

    logger.info("User deleted by admin", target_user=user_id, admin=str(admin.id))
    return {"message": f"User {user.email} and all their data deleted permanently"}


# ================================================================
# Job Monitoring (All Users)
# ================================================================

@router.get("/jobs")
async def list_all_jobs(
    status: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None, description="Filter by specific user"),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    _: User = Depends(get_current_admin),
):
    """Monitor all jobs across all users."""
    from app.schemas.responses import JobResponse

    query = {}
    if status:
        query["status"] = status
    if user_id:
        query["user_id"] = user_id

    jobs = await Job.find(query).sort("-created_at").skip(skip).limit(limit).to_list()

    result = []
    for job in jobs:
        job_data = JobResponse.from_job(job).model_dump()
        # Add user email for context
        owner = await User.get(job.user_id) if job.user_id else None
        job_data["user_email"] = owner.email if owner else "unknown"
        result.append(job_data)

    return result
