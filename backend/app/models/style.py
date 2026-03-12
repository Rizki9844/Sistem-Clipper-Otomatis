"""
Caption Style Document Model (Beanie ODM)
============================================
Customizable caption/subtitle styling templates.
Supports Hormozi-style word-by-word highlighting.
"""

from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import BaseModel, Field


class FontConfig(BaseModel):
    """Font configuration for captions."""
    family: str = "Montserrat"
    size: int = 48
    bold: bool = True
    italic: bool = False
    outline_width: int = 3
    shadow_depth: int = 2


class ColorConfig(BaseModel):
    """Color configuration using hex codes."""
    primary_text: str = "#FFFFFF"  # Main text color
    highlight_text: str = "#FFD700"  # Active word highlight (gold)
    outline: str = "#000000"  # Text outline
    shadow: str = "#000000"  # Text shadow
    background: Optional[str] = None  # Optional background box


class AnimationConfig(BaseModel):
    """Animation settings for word-by-word captions."""
    style: str = "word_highlight"  # word_highlight, pop_in, fade, karaoke, bounce
    highlight_duration_ms: int = 100  # Transition speed
    scale_factor: float = 1.15  # Scale up active word
    use_uppercase: bool = True  # UPPERCASE active word
    words_per_group: int = 3  # Words shown at a time


class PositionConfig(BaseModel):
    """Caption positioning on screen."""
    alignment: str = "bottom_center"  # top, center, bottom + left, center, right
    margin_x: int = 40  # Horizontal margin (pixels)
    margin_y: int = 120  # Vertical margin from edge (pixels)
    max_width: int = 900  # Max caption width (pixels)


class CaptionStyle(Document):
    """Reusable caption style template."""

    name: str
    description: str = ""
    is_default: bool = False

    font: FontConfig = Field(default_factory=FontConfig)
    colors: ColorConfig = Field(default_factory=ColorConfig)
    animation: AnimationConfig = Field(default_factory=AnimationConfig)
    position: PositionConfig = Field(default_factory=PositionConfig)

    # Preview thumbnail
    preview_url: Optional[str] = None

    # User info
    user_id: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "caption_styles"
        indexes = [
            "name",
            "is_default",
            "user_id",
        ]
