"""Authentication business logic — user creation and OAuth account linking."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import OAuthAccount, User
from app.schemas.user import OAuthVerifyRequest
from app.security.jwt import create_token_pair


async def get_or_create_oauth_user(
    db: AsyncSession,
    data: OAuthVerifyRequest,
) -> tuple[User, dict]:
    """
    Find an existing user by email or create a new one.
    Link the OAuth account if not already linked.
    Returns (user, token_pair).
    """
    # 1. Try to find existing user by email
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user is None:
        # 2. Create new user
        user = User(
            id=uuid.uuid4(),
            email=data.email,
            name=data.name,
            avatar_url=data.avatar_url,
            is_active=True,
        )
        db.add(user)
        await db.flush()  # Get the user ID without committing

    # 3. Check if this OAuth account is already linked
    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.user_id == user.id,
            OAuthAccount.provider == data.provider,
            OAuthAccount.provider_account_id == data.provider_account_id,
        )
    )
    existing_oauth = result.scalar_one_or_none()

    if existing_oauth is None:
        # 4. Link the OAuth account
        oauth_account = OAuthAccount(
            id=uuid.uuid4(),
            user_id=user.id,
            provider=data.provider,
            provider_account_id=data.provider_account_id,
            access_token=data.access_token,
        )
        db.add(oauth_account)
    else:
        # Update access token if provided
        if data.access_token:
            existing_oauth.access_token = data.access_token

    # 5. Update user profile data from OAuth if available
    if data.avatar_url and not user.avatar_url:
        user.avatar_url = data.avatar_url
    if data.name and user.name != data.name:
        user.name = data.name

    await db.flush()

    # 6. Generate JWT tokens
    token_pair = create_token_pair(str(user.id), user.email)

    return user, token_pair


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Fetch a user by their UUID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
