"""
Clips API Endpoints
======================
List, review, and manage generated video clips.
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Depends

from app.models.clip import Clip
from app.services.storage import AzureBlobStorage
from app.schemas.responses import ClipResponse
from app.api.deps import get_current_user
from app.models.user import User
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("api.clips")


@router.get("/", response_model=list[ClipResponse])
async def list_clips(
    video_id: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None, description="pending, approved, rejected"),
    min_score: Optional[float] = Query(None, ge=0, le=10),
    sort_by: str = Query("score", description="score, time, status"),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    """List clips owned by the current user."""
    query = {"user_id": str(current_user.id)}
    if video_id:
        query["video_id"] = video_id
    if job_id:
        query["job_id"] = job_id
    if status:
        query["status"] = status
    if review_status:
        query["review_status"] = review_status
    if min_score is not None:
        query["highlight_score"] = {"$gte": min_score}

    finder = Clip.find(query)

    sort_map = {"score": "-highlight_score", "time": "start_time", "status": "status"}
    sort_field = sort_map.get(sort_by, "-highlight_score")

    clips = await finder.sort(sort_field).skip(skip).limit(limit).to_list()
    return [ClipResponse.from_clip(c) for c in clips]


@router.get("/{clip_id}", response_model=ClipResponse)
async def get_clip(
    clip_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get clip details with download URL."""
    clip = await Clip.get(clip_id)
    if not clip or clip.user_id != str(current_user.id):
        raise HTTPException(status_code=404, detail="Clip not found")

    if clip.blob_name:
        storage = AzureBlobStorage()
        clip.blob_url = await storage.generate_sas_url(
            blob_name=clip.blob_name,
            container="processed-clips",
            expiry_hours=4,
        )
        await clip.save()

    return ClipResponse.from_clip(clip)


@router.post("/{clip_id}/review")
async def review_clip(
    clip_id: str,
    action: str = Query(..., description="approve or reject"),
    notes: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Approve or reject a generated clip."""
    clip = await Clip.get(clip_id)
    if not clip or clip.user_id != str(current_user.id):
        raise HTTPException(status_code=404, detail="Clip not found")

    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")

    clip.review_status = "approved" if action == "approve" else "rejected"
    if notes:
        clip.review_notes = notes
    clip.reviewed_at = datetime.utcnow()
    await clip.save()

    logger.info("Clip reviewed", clip_id=clip_id, action=action)
    return {"message": f"Clip {action}d successfully", "clip_id": clip_id, "review_status": clip.review_status}


@router.post("/batch-review")
async def batch_review(
    clip_ids: list[str],
    action: str = Query(..., description="approve or reject"),
    current_user: User = Depends(get_current_user),
):
    """Approve or reject multiple clips at once."""
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")

    updated = 0
    for cid in clip_ids:
        clip = await Clip.get(cid)
        if clip and clip.user_id == str(current_user.id):
            clip.review_status = "approved" if action == "approve" else "rejected"
            clip.reviewed_at = datetime.utcnow()
            await clip.save()
            updated += 1

    return {"message": f"{updated} clips {action}d", "updated": updated}


@router.get("/{clip_id}/download-url")
async def get_download_url(
    clip_id: str,
    expiry_hours: int = Query(4, ge=1, le=24),
    current_user: User = Depends(get_current_user),
):
    """Generate a temporary download URL for a clip."""
    clip = await Clip.get(clip_id)
    if not clip or clip.user_id != str(current_user.id):
        raise HTTPException(status_code=404, detail="Clip not found")

    if not clip.blob_name:
        raise HTTPException(status_code=400, detail="Clip has no associated file")

    storage = AzureBlobStorage()
    url = await storage.generate_sas_url(
        blob_name=clip.blob_name,
        container="processed-clips",
        expiry_hours=expiry_hours,
    )
    return {"download_url": url, "expires_in_hours": expiry_hours}


@router.delete("/{clip_id}")
async def delete_clip(
    clip_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a clip and its associated blob."""
    clip = await Clip.get(clip_id)
    if not clip or clip.user_id != str(current_user.id):
        raise HTTPException(status_code=404, detail="Clip not found")

    if clip.blob_name:
        storage = AzureBlobStorage()
        await storage.delete_blob("processed-clips", clip.blob_name)

    await clip.delete()
    logger.info("Clip deleted", clip_id=clip_id)
    return {"message": "Clip deleted"}


@router.get("/", response_model=list[ClipResponse])
async def list_clips(
    video_id: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None, description="pending, approved, rejected"),
    min_score: Optional[float] = Query(None, ge=0, le=10),
    sort_by: str = Query("score", description="score, time, status"),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
):
    """
    List clips with flexible filtering and sorting.
    Use video_id or job_id to get clips for a specific video/job.
    """
    query = {}
    if video_id:
        query["video_id"] = video_id
    if job_id:
        query["job_id"] = job_id
    if status:
        query["status"] = status
    if review_status:
        query["review_status"] = review_status

    finder = Clip.find(query)

    # Apply minimum score filter
    if min_score is not None:
        finder = Clip.find({**query, "highlight_score": {"$gte": min_score}})

    # Sort
    sort_map = {
        "score": "-highlight_score",
        "time": "start_time",
        "status": "status",
    }
    sort_field = sort_map.get(sort_by, "-highlight_score")

    clips = await finder.sort(sort_field).skip(skip).limit(limit).to_list()
    return [ClipResponse.from_clip(c) for c in clips]


@router.get("/{clip_id}", response_model=ClipResponse)
async def get_clip(clip_id: str):
    """Get clip details with download URL."""
    clip = await Clip.get(clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    # Generate temporary download URL
    if clip.blob_name:
        storage = AzureBlobStorage()
        clip.blob_url = await storage.generate_sas_url(
            blob_name=clip.blob_name,
            container="processed-clips",
            expiry_hours=4,
        )
        await clip.save()

    return ClipResponse.from_clip(clip)


@router.post("/{clip_id}/review")
async def review_clip(
    clip_id: str,
    action: str = Query(..., description="approve or reject"),
    notes: Optional[str] = Query(None, description="Optional reviewer notes"),
):
    """
    Human review: approve or reject a generated clip.
    Approved clips can be exported/published.
    """
    clip = await Clip.get(clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")

    clip.review_status = "approved" if action == "approve" else "rejected"
    if notes:
        clip.review_notes = notes
    clip.reviewed_at = datetime.utcnow()
    await clip.save()

    logger.info("Clip reviewed", clip_id=clip_id, action=action)

    return {
        "message": f"Clip {action}d successfully",
        "clip_id": clip_id,
        "review_status": clip.review_status,
    }


@router.post("/batch-review")
async def batch_review(
    clip_ids: list[str],
    action: str = Query(..., description="approve or reject"),
):
    """Approve or reject multiple clips at once."""
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")

    updated = 0
    for cid in clip_ids:
        clip = await Clip.get(cid)
        if clip:
            clip.review_status = "approved" if action == "approve" else "rejected"
            clip.reviewed_at = datetime.utcnow()
            await clip.save()
            updated += 1

    return {"message": f"{updated} clips {action}d", "updated": updated}


@router.get("/{clip_id}/download-url")
async def get_download_url(clip_id: str, expiry_hours: int = Query(4, ge=1, le=24)):
    """Generate a temporary download URL for a clip."""
    clip = await Clip.get(clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    if not clip.blob_name:
        raise HTTPException(status_code=400, detail="Clip has no associated file")

    storage = AzureBlobStorage()
    url = await storage.generate_sas_url(
        blob_name=clip.blob_name,
        container="processed-clips",
        expiry_hours=expiry_hours,
    )

    return {"download_url": url, "expires_in_hours": expiry_hours}


@router.delete("/{clip_id}")
async def delete_clip(clip_id: str):
    """Delete a clip and its associated blob."""
    clip = await Clip.get(clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    if clip.blob_name:
        storage = AzureBlobStorage()
        await storage.delete_blob("processed-clips", clip.blob_name)

    await clip.delete()
    logger.info("Clip deleted", clip_id=clip_id)

    return {"message": "Clip deleted"}
