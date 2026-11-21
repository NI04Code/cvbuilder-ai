"""Authentication business logic — user creation, OAuth account linking, and token refresh."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.database import profile_repo, user_repo
from app.models.user import User
from app.schemas.user import OAuthVerifyRequest, TokenResponse, UserResponse
from app.security.encryption import encrypt_secret
from app.security.jwt import create_token_pair, decode_token


async def get_or_create_oauth_user(
    db: AsyncSession,
    data: OAuthVerifyRequest,
) -> tuple[User, dict]:
    """
    Find an existing user by email or create a new one.
    Link the OAuth account if not already linked and issue JWT tokens.
    """
    user = await user_repo.get_user_by_email(db, data.email)

    if user is None:
        user = await user_repo.create_user(
            db,
            email=data.email,
            name=data.name,
            avatar_url=data.avatar_url,
        )

    existing_oauth = await user_repo.get_oauth_account(
        db,
        user_id=user.id,
        provider=data.provider,
        provider_account_id=data.provider_account_id,
    )

    encrypted_access_token = encrypt_secret(data.access_token)

    if existing_oauth is None:
        await user_repo.create_oauth_account(
            db,
            user_id=user.id,
            provider=data.provider,
            provider_account_id=data.provider_account_id,
            access_token=encrypted_access_token,
        )
    elif encrypted_access_token is not None:
        existing_oauth.access_token = encrypted_access_token

    if data.avatar_url and not user.avatar_url:
        user.avatar_url = data.avatar_url
    if data.name and user.name != data.name:
        user.name = data.name

    await user_repo.flush_changes(db)

    token_pair = create_token_pair(str(user.id), user.email)
    return user, token_pair


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Fetch a user by their UUID."""
    return await user_repo.get_user_by_id(db, user_id)


async def build_user_response(db: AsyncSession, user: User) -> UserResponse:
    """Build a UserResponse including explicit profile-existence check."""
    has_profile = await profile_repo.has_profile(db, user.id)

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        has_profile=has_profile,
        created_at=user.created_at,
    )


async def refresh_access_tokens(db: AsyncSession, refresh_token: str) -> TokenResponse:
    """Validate a refresh token and issue a rotated access + refresh token pair."""
    payload = decode_token(refresh_token)

    if payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid token type — refresh token required")

    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError("Invalid refresh token")

    try:
        uid = uuid.UUID(user_id)
    except ValueError as exc:
        raise UnauthorizedError("Invalid user identifier") from exc

    user = await user_repo.get_user_by_id(db, uid)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or deactivated")

    new_tokens = create_token_pair(str(user.id), user.email)
    return TokenResponse(**new_tokens)
