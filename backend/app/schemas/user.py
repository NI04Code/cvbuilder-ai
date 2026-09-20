"""Pydantic schemas for user-related request/response models."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ── Request Schemas ───────────────────────────────────────────────────────


class OAuthVerifyRequest(BaseModel):
    """Payload sent from NextAuth.js after a successful OAuth sign-in."""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    provider: str = Field(..., pattern=r"^(google|github)$")
    provider_account_id: str = Field(..., min_length=1, max_length=255)
    avatar_url: str | None = Field(None, max_length=2048)
    access_token: str | None = None  # Provider access token (optional)


class TokenRefreshRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


# ── Response Schemas ──────────────────────────────────────────────────────


class TokenResponse(BaseModel):
    """JWT token pair returned after authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


class UserResponse(BaseModel):
    """Public user data returned to the frontend."""

    id: uuid.UUID
    email: str
    name: str
    avatar_url: str | None = None
    is_active: bool
    has_profile: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """Combined auth response: user data + tokens."""

    user: UserResponse
    tokens: TokenResponse
