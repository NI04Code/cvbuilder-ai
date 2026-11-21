"""Authentication API endpoints — HTTP layer delegating to auth_service."""

import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import settings
from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    AuthResponse,
    OAuthVerifyRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.security.jwt import get_current_user
from app.security.rate_limiter import limiter
from app.services.auth_service import (
    build_user_response,
    get_or_create_oauth_user,
    refresh_access_tokens,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


def verify_internal_auth_secret(
    x_internal_auth_secret: str | None = Header(default=None, alias="X-Internal-Auth-Secret"),
) -> None:
    """Verify server-to-server secret between NextAuth and FastAPI."""
    expected = settings.internal_auth_secret
    if not expected:
        if settings.environment == "production":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal auth secret is not configured",
            )
        logger.warning(
            "INTERNAL_AUTH_SECRET is not set; skipping /auth/verify secret check in %s",
            settings.environment,
        )
        return

    if not x_internal_auth_secret or not hmac.compare_digest(x_internal_auth_secret, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal authentication secret",
        )


@router.post(
    "/verify",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify OAuth login and issue JWT tokens",
    dependencies=[Depends(verify_internal_auth_secret)],
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
        user=await build_user_response(db, user),
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
    """Exchange a valid refresh token for a rotated access + refresh token pair."""
    return await refresh_access_tokens(db, data.refresh_token)


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
    return await build_user_response(db, current_user)
