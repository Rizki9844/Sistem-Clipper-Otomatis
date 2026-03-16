"""
Stripe Service
================
Handles subscription checkout, webhook processing, and billing portal.
Uses Stripe API v12+ (stripe-python library).
"""

import stripe
from datetime import datetime, timedelta
from typing import Optional

from app.config import settings
from app.models.user import User
from app.services.plan_config import PLANS

stripe.api_key = settings.STRIPE_SECRET_KEY


async def create_checkout_session(user: User, tier: str) -> str:
    """
    Create a Stripe Checkout Session for upgrading to a given tier.
    Returns the checkout URL to redirect the user to.
    """
    if tier not in ("starter", "pro", "business"):
        raise ValueError(f"Invalid tier: {tier}")

    price_id_map = {
        "starter": settings.STRIPE_PRICE_STARTER,
        "pro": settings.STRIPE_PRICE_PRO,
        "business": settings.STRIPE_PRICE_BUSINESS,
    }
    price_id = price_id_map[tier]
    if not price_id:
        raise ValueError(f"Stripe price ID for '{tier}' not configured")

    # Reuse existing Stripe customer if available
    customer_id = user.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name or user.email,
            metadata={"user_id": str(user.id)},
        )
        customer_id = customer.id
        user.stripe_customer_id = customer_id
        await user.save()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=settings.STRIPE_SUCCESS_URL + f"&tier={tier}",
        cancel_url=settings.STRIPE_CANCEL_URL,
        metadata={"user_id": str(user.id), "tier": tier},
        subscription_data={
            "metadata": {"user_id": str(user.id), "tier": tier},
        },
        allow_promotion_codes=True,
    )
    return session.url


async def create_billing_portal_session(user: User) -> str:
    """
    Create a Stripe Billing Portal session so user can manage/cancel subscription.
    Returns the portal URL.
    """
    if not user.stripe_customer_id:
        raise ValueError("No Stripe customer found for this user")

    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=settings.STRIPE_SUCCESS_URL.replace("?success=true", ""),
    )
    return session.url


async def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """
    Process incoming Stripe webhook event.
    Validates signature and updates user plan accordingly.
    Returns dict with event type and result.
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise ValueError("Invalid Stripe webhook signature")

    event_type = event["type"]
    data_obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        await _on_checkout_completed(data_obj)

    elif event_type == "customer.subscription.updated":
        await _on_subscription_updated(data_obj)

    elif event_type == "customer.subscription.deleted":
        await _on_subscription_deleted(data_obj)

    elif event_type == "invoice.payment_failed":
        await _on_payment_failed(data_obj)

    return {"event": event_type, "status": "processed"}


# ---------------------------------------------------------------------------
# Internal webhook handlers
# ---------------------------------------------------------------------------

async def _on_checkout_completed(session: dict):
    """User completed checkout — upgrade their plan."""
    user_id = session.get("metadata", {}).get("user_id")
    tier = session.get("metadata", {}).get("tier")
    subscription_id = session.get("subscription")

    if not user_id or not tier:
        return

    user = await User.get(user_id)
    if not user:
        return

    plan = PLANS.get(tier, PLANS["free"])
    user.plan_tier = tier
    user.monthly_quota = plan["monthly_quota"]
    user.stripe_subscription_id = subscription_id
    user.subscription_status = "active"
    user.trial_end_date = None
    await user.save()


async def _on_subscription_updated(subscription: dict):
    """Subscription changed (upgrade/downgrade/trial end)."""
    user_id = subscription.get("metadata", {}).get("user_id")
    if not user_id:
        # Try to find by customer ID
        customer_id = subscription.get("customer")
        user = await User.find_one(User.stripe_customer_id == customer_id)
    else:
        user = await User.get(user_id)

    if not user:
        return

    stripe_status = subscription.get("status")  # active | trialing | past_due | canceled
    user.subscription_status = stripe_status

    if stripe_status == "trialing":
        trial_end_ts = subscription.get("trial_end")
        if trial_end_ts:
            user.trial_end_date = datetime.utcfromtimestamp(trial_end_ts)

    elif stripe_status in ("canceled", "unpaid"):
        # Downgrade to free
        user.plan_tier = "free"
        user.monthly_quota = PLANS["free"]["monthly_quota"]
        user.stripe_subscription_id = None

    await user.save()


async def _on_subscription_deleted(subscription: dict):
    """Subscription fully canceled — downgrade to free."""
    customer_id = subscription.get("customer")
    user = await User.find_one(User.stripe_customer_id == customer_id)
    if not user:
        return

    user.plan_tier = "free"
    user.monthly_quota = PLANS["free"]["monthly_quota"]
    user.stripe_subscription_id = None
    user.subscription_status = "inactive"
    user.trial_end_date = None
    await user.save()


async def _on_payment_failed(invoice: dict):
    """Mark subscription as past_due."""
    customer_id = invoice.get("customer")
    user = await User.find_one(User.stripe_customer_id == customer_id)
    if not user:
        return

    user.subscription_status = "past_due"
    await user.save()
