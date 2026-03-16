"""
Auth API Endpoints
====================
Register, login, profile management.
All other endpoints require the JWT token issued here.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status
from starlette.requests import Request

from app.models.user import User
from app.schemas.auth import (
    RegisterRequest, LoginRequest, ChangePasswordRequest,
    TokenResponse, UserResponse,
)
from app.services.auth_service import hash_password, verify_password, create_access_token
from app.api.deps import get_current_user
from app.api.rate_limit import limiter
from app.config import settings
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("api.auth")


# ============================================================
# Register
# ============================================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
async def register(request: Request, body: RegisterRequest):
    """
    Create a new user account.
    Email must be unique. Password is bcrypt-hashed before storage.
    """
    existing = await User.find_one(User.email == body.email.lower())
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=body.email.lower().strip(),
        hashed_password=hash_password(body.password),
        full_name=body.full_name.strip(),
    )
    await user.insert()

    logger.info("User registered", user_id=str(user.id), email=user.email)

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
        created_at=user.created_at,
        last_login=user.last_login,
    )


# ============================================================
# Login
# ============================================================

@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(request: Request, body: LoginRequest):
    """
    Authenticate with email + password.
    Returns a JWT access token valid for JWT_EXPIRE_MINUTES.
    Use this token as: Authorization: Bearer <token>
    """
    user = await User.find_one(User.email == body.email.lower())

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Update last login
    await user.set({User.last_login: datetime.utcnow()})

    token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        is_admin=user.is_admin,
    )

    logger.info("User logged in", user_id=str(user.id), email=user.email)

    return TokenResponse(
        access_token=token,
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
    )


# ============================================================
# Current User Profile
# ============================================================

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the authenticated user's profile."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
    )


# ============================================================
# Change Password
# ============================================================

@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("3/minute")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
):
    """Change the current user's password."""
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    await current_user.set({User.hashed_password: hash_password(body.new_password)})
    logger.info("Password changed", user_id=str(current_user.id))


# ============================================================
# Quota Info
# ============================================================

@router.get("/me/quota")
async def get_quota(current_user: User = Depends(get_current_user)):
    """Get the current user's quota usage for this month."""
    from datetime import datetime
    now = datetime.utcnow()

    # Auto-reset if new month
    if now.year > current_user.quota_reset_date.year or now.month > current_user.quota_reset_date.month:
        current_user.used_quota = 0
        current_user.quota_reset_date = now
        await current_user.save()

    return {
        "plan_tier": current_user.plan_tier,
        "used": current_user.used_quota,
        "limit": current_user.monthly_quota,
        "unlimited": current_user.monthly_quota == 0,
        "remaining": max(0, current_user.monthly_quota - current_user.used_quota) if current_user.monthly_quota > 0 else None,
        "reset_date": current_user.quota_reset_date.isoformat(),
    }
