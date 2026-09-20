"""Authentication API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.profile import Profile
from app.models.user import User
from app.schemas.user import (
    AuthResponse,
    OAuthVerifyRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.security.jwt import create_token_pair, decode_token, get_current_user
from app.security.rate_limiter import limiter
from app.services.auth_service import get_or_create_oauth_user, get_user_by_id

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def _user_response(db: AsyncSession, user: User) -> UserResponse:
    """Build a UserResponse, checking profile existence via explicit query."""
    result = await db.execute(
        select(Profile.id).where(Profile.user_id == user.id).limit(1)
    )
    has_profile = result.scalar_one_or_none() is not None

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        has_profile=has_profile,
        created_at=user.created_at,
    )


@router.post(
    "/verify",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify OAuth login and issue JWT tokens",
)
@limiter.limit("10/minute")
async def verify_oauth(
    request: Request,
    data: OAuthVerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """
    Called by the frontend after a successful NextAuth.js OAuth sign-in.
    Creates or finds the user in the backend DB and returns JWT tokens.
    """
    user, token_pair = await get_or_create_oauth_user(db, data)

    return AuthResponse(
        user=await _user_response(db, user),
        tokens=TokenResponse(**token_pair),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token using a valid refresh token",
)
@limiter.limit("5/minute")
async def refresh_token(
    request: Request,
    data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    Implements token rotation for security.
    """
    payload = decode_token(data.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — refresh token required",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identifier",
        )

    user = await get_user_by_id(db, uid)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )

    # Issue new token pair (rotation)
    new_tokens = create_token_pair(str(user.id), user.email)
    return TokenResponse(**new_tokens)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Return the currently authenticated user's data."""
    return await _user_response(db, current_user)
