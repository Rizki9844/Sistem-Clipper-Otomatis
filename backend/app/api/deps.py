"""
FastAPI Dependencies
======================
Reusable dependencies for auth-protected endpoints.
Import and use with: Depends(get_current_user)
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime
from typing import Callable

from app.models.user import User
from app.services.auth_service import decode_access_token
from app.services.plan_config import get_plan, tier_gte, PLANS

_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> User:
    """
    Extract and validate the JWT from the Authorization: Bearer <token> header.
    Raises 401 if missing, invalid, or expired.
    Raises 403 if user account is deactivated.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if not user_id:
        raise credentials_exception

    user = await User.get(user_id)
    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Auto-promote trial users: if trial_end_date passed, downgrade to free
    if (
        user.plan_tier == "pro"
        and user.subscription_status == "trialing"
        and user.trial_end_date
        and datetime.utcnow() > user.trial_end_date
    ):
        user.plan_tier = "free"
        user.subscription_status = "inactive"
        user.monthly_quota = PLANS["free"]["monthly_quota"]
        await user.save()

    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the current user to be an admin. Raises 403 otherwise."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def check_quota(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Check if the user has remaining quota for submitting a new job.
    Resets monthly quota automatically when a new month starts.
    monthly_quota == 0 means unlimited (pro/business/enterprise).
    """
    now = datetime.utcnow()

    # Reset quota if a new month has started since last reset
    if now.year > current_user.quota_reset_date.year or now.month > current_user.quota_reset_date.month:
        current_user.used_quota = 0
        current_user.quota_reset_date = now
        await current_user.save()

    # 0 = unlimited
    if current_user.monthly_quota == 0:
        return current_user

    if current_user.used_quota >= current_user.monthly_quota:
        plan = get_plan(current_user.plan_tier)
        next_tier = _next_tier(current_user.plan_tier)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "QUOTA_EXCEEDED",
                "message": (
                    f"Monthly quota exceeded ({current_user.used_quota}/{current_user.monthly_quota} videos). "
                    f"Upgrade to {next_tier.title()} to get more."
                ),
                "used": current_user.used_quota,
                "limit": current_user.monthly_quota,
                "current_plan": current_user.plan_tier,
                "upgrade_to": next_tier,
            },
        )

    return current_user


def require_feature(feature: str, required_tier: str = "starter") -> Callable:
    """
    Factory dependency: gates an endpoint behind a minimum plan tier.

    Usage:
        @router.post("/publish")
        async def publish(user: User = Depends(require_feature("publish_platforms", "starter"))):
            ...
    """
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        # Admin/enterprise always passes
        if current_user.is_admin or current_user.plan_tier == "enterprise":
            return current_user

        if not tier_gte(current_user.plan_tier, required_tier):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FEATURE_LOCKED",
                    "message": f"This feature requires the {required_tier.title()} plan or higher.",
                    "feature": feature,
                    "current_plan": current_user.plan_tier,
                    "required_plan": required_tier,
                },
            )
        return current_user

    return _check


def _next_tier(tier: str) -> str:
    """Return the next higher tier name."""
    from app.services.plan_config import TIER_ORDER
    try:
        idx = TIER_ORDER.index(tier)
        return TIER_ORDER[idx + 1] if idx + 1 < len(TIER_ORDER) else tier
    except ValueError:
        return "pro"

