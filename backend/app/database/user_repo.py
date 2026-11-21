"""Database queries for User and OAuthAccount models."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import OAuthAccount, User


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Fetch a user by UUID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Fetch a user by email address."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    name: str,
    avatar_url: str | None,
) -> User:
    """Persist a new User record and flush to obtain its ID."""
    user = User(
        id=uuid.uuid4(),
        email=email,
        name=name,
        avatar_url=avatar_url,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


async def get_oauth_account(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    provider: str,
    provider_account_id: str,
) -> OAuthAccount | None:
    """Fetch an existing OAuthAccount link for a user and provider."""
    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.user_id == user_id,
            OAuthAccount.provider == provider,
            OAuthAccount.provider_account_id == provider_account_id,
        )
    )
    return result.scalar_one_or_none()


async def create_oauth_account(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    provider: str,
    provider_account_id: str,
    access_token: str | None,
) -> OAuthAccount:
    """Create and stage a new OAuthAccount link."""
    oauth_account = OAuthAccount(
        id=uuid.uuid4(),
        user_id=user_id,
        provider=provider,
        provider_account_id=provider_account_id,
        access_token=access_token,
    )
    db.add(oauth_account)
    return oauth_account


async def flush_changes(db: AsyncSession) -> None:
    """Flush pending user/OAuth changes within the active transaction."""
    await db.flush()
