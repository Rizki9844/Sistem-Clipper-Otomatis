"""
User Document Model (Beanie ODM)
===================================
Multi-tenant user accounts for AutoClipperPro.
Passwords are stored as bcrypt hashes — never plaintext.
"""

from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import Field, EmailStr


class User(Document):
    """Registered user account."""

    email: str  # Unique, used as login identifier
    hashed_password: str
    full_name: str = ""

    is_active: bool = True
    is_admin: bool = False  # Admins can manage styles, see all users' jobs

    # --- Quota & Subscription ---
    plan_tier: str = "free"              # "free" | "starter" | "pro" | "business" | "enterprise"
    monthly_quota: int = 3               # max videos/month; 0 = unlimited
    used_quota: int = 0                  # videos submitted this month
    quota_reset_date: datetime = Field(default_factory=datetime.utcnow)

    # --- Stripe ---
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    subscription_status: str = "inactive"  # "active" | "trialing" | "past_due" | "canceled" | "inactive"
    trial_end_date: Optional[datetime] = None

    # --- Connected Social Accounts (platform names list) ---
    connected_platforms: list[str] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    class Settings:
        name = "users"
        indexes = [
            "email",     # unique lookup
            "is_active",
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "full_name": "John Doe",
            }
        }
