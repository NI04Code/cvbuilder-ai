"""Database queries for JobApplication persistence (strictly scoped by user_id)."""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_application import JobApplication


async def list_applications(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    status_filter: str | None = None,
    search_query: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[JobApplication]:
    """Return paginated job applications owned by user_id ordered by most recently updated."""
    stmt = select(JobApplication).where(JobApplication.user_id == user_id)

    if status_filter:
        stmt = stmt.where(JobApplication.status == status_filter)

    if search_query and search_query.strip():
        pattern = f"%{search_query.strip()}%"
        stmt = stmt.where(
            or_(
                JobApplication.company_name.ilike(pattern),
                JobApplication.role_title.ilike(pattern),
                JobApplication.location.ilike(pattern),
            )
        )

    stmt = (
        stmt.order_by(JobApplication.updated_at.desc(), JobApplication.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_by_status(db: AsyncSession, user_id: uuid.UUID) -> dict[str, int]:
    """Return application counts grouped by status for user_id."""
    result = await db.execute(
        select(JobApplication.status, func.count(JobApplication.id))
        .where(JobApplication.user_id == user_id)
        .group_by(JobApplication.status)
    )
    return {status_key: int(count) for status_key, count in result.all()}


async def get_owned_application(
    db: AsyncSession,
    application_id: uuid.UUID,
    user_id: uuid.UUID,
) -> JobApplication | None:
    """Load a single job application row scoped strictly to user_id."""
    result = await db.execute(
        select(JobApplication).where(
            JobApplication.id == application_id,
            JobApplication.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def create_application(
    db: AsyncSession,
    record: JobApplication,
) -> JobApplication:
    """Persist a new JobApplication row, commit, and refresh."""
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def update_application(
    db: AsyncSession,
    record: JobApplication,
) -> JobApplication:
    """Flush modifications on an existing JobApplication row, commit, and refresh."""
    await db.commit()
    await db.refresh(record)
    return record


async def delete_application(
    db: AsyncSession,
    record: JobApplication,
) -> None:
    """Delete an existing JobApplication row and commit."""
    await db.delete(record)
    await db.commit()
