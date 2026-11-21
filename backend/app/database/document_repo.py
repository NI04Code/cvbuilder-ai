"""Database queries for generated document models (GeneratedCV, GeneratedCoverLetter)."""

import uuid
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

DocModelT = TypeVar("DocModelT")


async def get_owned_document(
    db: AsyncSession,
    model_cls: type[DocModelT],
    doc_id: uuid.UUID,
    user_id: uuid.UUID,
) -> DocModelT | None:
    """Load a generated document row scoped strictly to the owning user."""
    result = await db.execute(
        select(model_cls).where(model_cls.id == doc_id, model_cls.user_id == user_id)  # type: ignore[attr-defined]
    )
    return result.scalar_one_or_none()


async def list_by_user(
    db: AsyncSession,
    model_cls: type[DocModelT],
    user_id: uuid.UUID,
    *,
    limit: int,
    offset: int = 0,
) -> list[DocModelT]:
    """Return paginated document rows owned by user_id ordered newest-first."""
    result = await db.execute(
        select(model_cls)
        .where(model_cls.user_id == user_id)  # type: ignore[attr-defined]
        .order_by(model_cls.created_at.desc())  # type: ignore[attr-defined]
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def save_document(db: AsyncSession, record: DocModelT) -> DocModelT:
    """Insert a generated document row, commit, and refresh."""
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def delete_document(db: AsyncSession, record: DocModelT) -> None:
    """Delete a generated document row and commit."""
    await db.delete(record)
    await db.commit()
