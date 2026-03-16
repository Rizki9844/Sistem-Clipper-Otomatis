"""
Billing API Endpoints
=======================
Stripe checkout, billing portal, plans info, and webhook receiver.

Routes:
  GET  /billing/plans              — daftar semua plan (public)
  POST /billing/checkout/{tier}    — buat Stripe Checkout Session
  POST /billing/portal             — buka Billing Portal (manage/cancel)
  GET  /billing/status             — status subscription user saat ini
  POST /billing/webhook            — Stripe webhook receiver (no auth)
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from datetime import datetime

from app.api.deps import get_current_user
from app.models.user import User
from app.services.stripe_service import (
    create_checkout_session,
    create_billing_portal_session,
    handle_webhook,
)
from app.services.plan_config import PLANS, PRICING_DISPLAY, get_plan

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


class SubscriptionStatus(BaseModel):
    plan_tier: str
    subscription_status: str
    monthly_quota: int
    used_quota: int
    trial_end_date: datetime | None
    features: dict
    is_trial: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/plans")
async def list_plans():
    """Return all available plans with features and pricing (public endpoint)."""
    return {
        "plans": PRICING_DISPLAY,
        "prices": {
            tier: data["price_monthly"]
            for tier, data in PLANS.items()
            if tier not in ("enterprise",)
        },
    }


@router.post("/checkout/{tier}", response_model=CheckoutResponse)
async def create_checkout(
    tier: str,
    current_user: User = Depends(get_current_user),
):
    """
    Create a Stripe Checkout Session for upgrading to the given tier.
    Returns a redirect URL for the frontend to redirect to.
    """
    if tier not in ("starter", "pro", "business"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier '{tier}'. Choose: starter, pro, business",
        )

    # Already on this plan or higher
    from app.services.plan_config import tier_gte, TIER_ORDER
    if tier_gte(current_user.plan_tier, tier) and current_user.plan_tier != "free":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You are already on the {current_user.plan_tier} plan",
        )

    try:
        checkout_url = await create_checkout_session(current_user, tier)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return CheckoutResponse(checkout_url=checkout_url)


@router.post("/portal", response_model=PortalResponse)
async def billing_portal(current_user: User = Depends(get_current_user)):
    """
    Open Stripe Billing Portal for managing/canceling subscription.
    Only available to users who have a Stripe customer ID.
    """
    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription found. Upgrade first.",
        )

    try:
        portal_url = await create_billing_portal_session(current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return PortalResponse(portal_url=portal_url)


@router.get("/status", response_model=SubscriptionStatus)
async def get_subscription_status(current_user: User = Depends(get_current_user)):
    """Return full subscription status including plan features."""
    plan = get_plan(current_user.plan_tier)
    is_trial = (
        current_user.subscription_status == "trialing"
        and current_user.trial_end_date is not None
        and current_user.trial_end_date > datetime.utcnow()
    )
    return SubscriptionStatus(
        plan_tier=current_user.plan_tier,
        subscription_status=current_user.subscription_status,
        monthly_quota=current_user.monthly_quota,
        used_quota=current_user.used_quota,
        trial_end_date=current_user.trial_end_date,
        features=plan,
        is_trial=is_trial,
    )


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request):
    """
    Stripe webhook receiver. Validates signature and processes events.
    IMPORTANT: Must be registered BEFORE any middleware strips the raw body.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        result = await handle_webhook(payload, sig_header)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {"received": True, **result}
