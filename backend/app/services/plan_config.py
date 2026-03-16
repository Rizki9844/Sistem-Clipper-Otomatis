"""
Plan Configuration & Feature Flags
=====================================
Single source of truth untuk semua tier plan AutoClipperPro.
Feature flags dicek via `check_feature` dependency di deps.py.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Plan Definitions
# ---------------------------------------------------------------------------

PLANS: dict[str, dict[str, Any]] = {
    "free": {
        "display_name": "Free",
        "price_monthly": 0,
        "monthly_quota": 3,                 # max video submissions per month
        "max_video_duration_minutes": 30,   # 0 = unlimited
        "max_clips_per_video": 3,           # 0 = unlimited
        "max_quality": "720p",
        "watermark": True,                  # AutoClipperPro watermark on output
        "publish_platforms": [],            # no social publish
        "queue_priority": 3,               # higher number = lower priority
        "custom_captions": False,
        "caption_styles": 1,               # only 1 caption style allowed
        "analytics": False,
        "api_access": False,
        "team_seats": 1,
        "trial_days": 7,                   # Pro trial on first register
        "stripe_price_id": None,
    },
    "starter": {
        "display_name": "Starter",
        "price_monthly": 12,
        "monthly_quota": 20,
        "max_video_duration_minutes": 120,
        "max_clips_per_video": 10,
        "max_quality": "1080p",
        "watermark": False,
        "publish_platforms": ["tiktok"],    # 1 platform only
        "queue_priority": 2,
        "custom_captions": True,
        "caption_styles": 3,
        "analytics": "basic",
        "api_access": False,
        "team_seats": 1,
        "trial_days": 0,
        "stripe_price_id": None,            # set via STRIPE_PRICE_STARTER env
    },
    "pro": {
        "display_name": "Pro",
        "price_monthly": 29,
        "monthly_quota": 60,
        "max_video_duration_minutes": 240,
        "max_clips_per_video": 20,
        "max_quality": "1080p",
        "watermark": False,
        "publish_platforms": ["tiktok", "instagram", "youtube"],
        "queue_priority": 1,
        "custom_captions": True,
        "caption_styles": 0,               # unlimited
        "analytics": "full",
        "api_access": False,
        "team_seats": 1,
        "trial_days": 0,
        "stripe_price_id": None,            # set via STRIPE_PRICE_PRO env
    },
    "business": {
        "display_name": "Business",
        "price_monthly": 79,
        "monthly_quota": 0,                # unlimited
        "max_video_duration_minutes": 0,   # unlimited
        "max_clips_per_video": 0,          # unlimited
        "max_quality": "4k",
        "watermark": False,
        "publish_platforms": ["tiktok", "instagram", "youtube"],
        "queue_priority": 1,
        "custom_captions": True,
        "caption_styles": 0,
        "analytics": "full",
        "api_access": True,
        "team_seats": 5,
        "trial_days": 0,
        "stripe_price_id": None,            # set via STRIPE_PRICE_BUSINESS env
    },
    # Admin/owner internal tier — bypasses ALL restrictions
    "enterprise": {
        "display_name": "Enterprise",
        "price_monthly": 0,
        "monthly_quota": 0,
        "max_video_duration_minutes": 0,
        "max_clips_per_video": 0,
        "max_quality": "4k",
        "watermark": False,
        "publish_platforms": ["tiktok", "instagram", "youtube"],
        "queue_priority": 0,
        "custom_captions": True,
        "caption_styles": 0,
        "analytics": "full",
        "api_access": True,
        "team_seats": 0,                   # unlimited
        "trial_days": 0,
        "stripe_price_id": None,
    },
}

# Tier order for comparison (higher index = higher tier)
TIER_ORDER = ["free", "starter", "pro", "business", "enterprise"]


def get_plan(tier: str) -> dict[str, Any]:
    """Get plan config dict. Falls back to 'free' if unknown tier."""
    return PLANS.get(tier, PLANS["free"])


def tier_gte(user_tier: str, required_tier: str) -> bool:
    """Check if user_tier is >= required_tier in hierarchy."""
    try:
        return TIER_ORDER.index(user_tier) >= TIER_ORDER.index(required_tier)
    except ValueError:
        return False


def can_use_platform(user_tier: str, platform: str) -> bool:
    """Check if user's plan allows publishing to a specific platform."""
    plan = get_plan(user_tier)
    return platform in plan["publish_platforms"]


# ---------------------------------------------------------------------------
# Pricing page display config
# ---------------------------------------------------------------------------

PRICING_DISPLAY = [
    {
        "tier": "free",
        "badge": None,
        "cta": "Get Started Free",
        "features": [
            "3 videos/month",
            "Max 30-min videos",
            "3 clips per video",
            "720p output",
            "AutoClipperPro watermark",
            "7-day Pro trial",
        ],
        "not_included": [
            "No social publishing",
            "No custom captions",
            "No analytics",
            "Slow processing queue",
        ],
    },
    {
        "tier": "starter",
        "badge": None,
        "cta": "Start Starter",
        "features": [
            "20 videos/month",
            "Max 2-hour videos",
            "10 clips per video",
            "1080p output",
            "No watermark",
            "Publish to TikTok",
            "Custom caption styles",
        ],
        "not_included": [
            "Instagram & YouTube publish",
            "No API access",
        ],
    },
    {
        "tier": "pro",
        "badge": "Most Popular",
        "cta": "Go Pro",
        "features": [
            "60 videos/month",
            "Max 4-hour videos",
            "20 clips per video",
            "1080p 60fps output",
            "No watermark",
            "Publish to TikTok + Instagram + YouTube",
            "All caption styles",
            "Full analytics",
            "Priority processing queue",
        ],
        "not_included": [
            "No API access",
            "1 seat only",
        ],
    },
    {
        "tier": "business",
        "badge": "Best Value",
        "cta": "Get Business",
        "features": [
            "Unlimited videos",
            "Unlimited video length",
            "Unlimited clips",
            "4K output",
            "No watermark",
            "Publish to all platforms",
            "All caption styles",
            "Full analytics + export",
            "Priority processing queue",
            "API access",
            "5 team seats",
        ],
        "not_included": [],
    },
]
