"""Business logic for job applications tracking CRUD and pipeline summary stats."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.database import job_applications_repo
from app.models.job_application import JobApplication
from app.schemas.job_applications import (
    ApplicationCreateRequest,
    ApplicationStatsResponse,
    ApplicationUpdateRequest,
)


async def create_user_application(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: ApplicationCreateRequest,
) -> JobApplication:
    """Create a tracked job application owned by user_id."""
    now = datetime.now(timezone.utc)
    record = JobApplication(
        id=uuid.uuid4(),
        user_id=user_id,
        company_name=data.company_name,
        role_title=data.role_title,
        job_url=data.job_url,
        status=data.status,
        applied_date=data.applied_date,
        work_mode=data.work_mode,
        location=data.location,
        salary_range=data.salary_range,
        recruiter_name=data.recruiter_name,
        recruiter_contact=data.recruiter_contact,
        next_follow_up_date=data.next_follow_up_date,
        notes=data.notes,
        created_at=now,
        updated_at=now,
    )
    return await job_applications_repo.create_application(db, record)


async def list_user_applications(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    status_filter: str | None = None,
    search_query: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[JobApplication]:
    """Return paginated job applications owned by user_id."""
    return await job_applications_repo.list_applications(
        db,
        user_id,
        status_filter=status_filter,
        search_query=search_query,
        limit=limit,
        offset=offset,
    )


async def get_user_application_stats(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> ApplicationStatsResponse:
    """Compute pipeline counts per status for user_id."""
    counts = await job_applications_repo.count_by_status(db, user_id)
    saved = counts.get("saved", 0)
    applied = counts.get("applied", 0)
    interviewing = counts.get("interviewing", 0)
    offer = counts.get("offer", 0)
    rejected = counts.get("rejected", 0)
    withdrawn = counts.get("withdrawn", 0)
    total = saved + applied + interviewing + offer + rejected + withdrawn
    return ApplicationStatsResponse(
        total=total,
        saved=saved,
        applied=applied,
        interviewing=interviewing,
        offer=offer,
        rejected=rejected,
        withdrawn=withdrawn,
    )


async def get_user_application(
    db: AsyncSession,
    application_id: uuid.UUID,
    user_id: uuid.UUID,
) -> JobApplication:
    """Fetch a single job application owned by user_id, raising NotFoundError if absent."""
    record = await job_applications_repo.get_owned_application(db, application_id, user_id)
    if not record:
        raise NotFoundError("Application not found")
    return record


async def update_user_application(
    db: AsyncSession,
    application_id: uuid.UUID,
    user_id: uuid.UUID,
    data: ApplicationUpdateRequest,
) -> JobApplication:
    """Apply partial updates to an owned job application."""
    record = await get_user_application(db, application_id, user_id)
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(record, field, value)
    record.updated_at = datetime.now(timezone.utc)
    return await job_applications_repo.update_application(db, record)


async def delete_user_application(
    db: AsyncSession,
    application_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Delete an owned job application."""
    record = await get_user_application(db, application_id, user_id)
    await job_applications_repo.delete_application(db, record)
