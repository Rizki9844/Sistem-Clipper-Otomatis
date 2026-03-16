"""
Auth Schemas
==============
Pydantic request/response schemas for authentication endpoints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ---- Request Schemas ----

class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email (used for login)")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    full_name: str = Field(default="", description="Display name")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
                "full_name": "John Doe",
            }
        }


class LoginRequest(BaseModel):
    email: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
            }
        }


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


# ---- Response Schemas ----

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime] = None
