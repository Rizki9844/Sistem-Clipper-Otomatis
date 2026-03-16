"""
Caption Styles API Endpoints
===============================
CRUD for caption style templates.
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.models.style import (
    CaptionStyle,
    FontConfig,
    ColorConfig,
    AnimationConfig,
    PositionConfig,
)
from app.api.deps import get_current_user, get_current_admin
from app.models.user import User

router = APIRouter()


class StyleCreateRequest(BaseModel):
    name: str
    description: str = ""
    font: FontConfig = FontConfig()
    colors: ColorConfig = ColorConfig()
    animation: AnimationConfig = AnimationConfig()
    position: PositionConfig = PositionConfig()


class StyleResponse(BaseModel):
    id: str
    name: str
    description: str
    is_default: bool
    font: FontConfig
    colors: ColorConfig
    animation: AnimationConfig
    position: PositionConfig
    created_at: datetime


@router.get("/", response_model=list[StyleResponse])
async def list_styles(_: User = Depends(get_current_user)):
    """List all caption style templates (shared across all users)."""
    styles = await CaptionStyle.find_all().sort("name").to_list()
    return [
        StyleResponse(
            id=str(s.id), name=s.name, description=s.description,
            is_default=s.is_default, font=s.font, colors=s.colors,
            animation=s.animation, position=s.position, created_at=s.created_at,
        )
        for s in styles
    ]


@router.post("/", response_model=StyleResponse)
async def create_style(
    data: StyleCreateRequest,
    _: User = Depends(get_current_admin),
):
    """Create a new caption style template. Admin only."""
    style = CaptionStyle(**data.model_dump())
    await style.insert()
    return StyleResponse(
        id=str(style.id), name=style.name, description=style.description,
        is_default=style.is_default, font=style.font, colors=style.colors,
        animation=style.animation, position=style.position, created_at=style.created_at,
    )


@router.put("/{style_id}", response_model=StyleResponse)
async def update_style(
    style_id: str,
    data: StyleCreateRequest,
    _: User = Depends(get_current_admin),
):
    """Update a caption style template. Admin only."""
    style = await CaptionStyle.get(style_id)
    if not style:
        raise HTTPException(status_code=404, detail="Style not found")

    style.name = data.name
    style.description = data.description
    style.font = data.font
    style.colors = data.colors
    style.animation = data.animation
    style.position = data.position
    style.updated_at = datetime.utcnow()
    await style.save()

    return StyleResponse(
        id=str(style.id), name=style.name, description=style.description,
        is_default=style.is_default, font=style.font, colors=style.colors,
        animation=style.animation, position=style.position, created_at=style.created_at,
    )


@router.delete("/{style_id}")
async def delete_style(
    style_id: str,
    _: User = Depends(get_current_admin),
):
    """Delete a caption style template. Admin only."""
    style = await CaptionStyle.get(style_id)
    if not style:
        raise HTTPException(status_code=404, detail="Style not found")
    if style.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete default style")

    await style.delete()
    return {"message": "Style deleted successfully"}
