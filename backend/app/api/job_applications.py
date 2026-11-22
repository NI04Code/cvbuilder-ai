"""Job Applications Tracker API endpoints — HTTP layer delegating to job_applications_service."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.job_applications import (
    ApplicationCreateRequest,
    ApplicationResponse,
    ApplicationStatsResponse,
    ApplicationStatus,
    ApplicationUpdateRequest,
)
from app.security.jwt import get_current_user
from app.services.job_applications_service import (
    create_user_application,
    delete_user_application,
    get_user_application,
    get_user_application_stats,
    list_user_applications,
    update_user_application,
)

router = APIRouter(prefix="/job-applications", tags=["Job Applications"])


@router.get(
    "/stats",
    response_model=ApplicationStatsResponse,
    summary="Get pipeline counts by status for the authenticated user",
)
async def get_application_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationStatsResponse:
    """Return status summary counts for the user's tracked job applications."""
    return await get_user_application_stats(db, current_user.id)


@router.get(
    "",
    response_model=list[ApplicationResponse],
    summary="List tracked job applications for the authenticated user",
)
async def list_applications(
    status_filter: ApplicationStatus | None = Query(
        None, alias="status", description="Optional pipeline status filter"
    ),
    q: str | None = Query(
        None, max_length=100, description="Optional search term matching company, role, or location"
    ),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ApplicationResponse]:
    """Return paginated tracked job applications owned by the authenticated user."""
    items = await list_user_applications(
        db,
        current_user.id,
        status_filter=status_filter,
        search_query=q,
        limit=limit,
        offset=offset,
    )
    return [ApplicationResponse.model_validate(item) for item in items]


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tracked job application",
)
async def create_application(
    data: ApplicationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    """Create a job application record owned by the authenticated user."""
    record = await create_user_application(db, current_user.id, data)
    return ApplicationResponse.model_validate(record)


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="Get a tracked job application",
)
async def get_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    """Fetch a single tracked job application owned by the authenticated user."""
    record = await get_user_application(db, application_id, current_user.id)
    return ApplicationResponse.model_validate(record)


@router.patch(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="Update a tracked job application",
)
async def update_application(
    application_id: uuid.UUID,
    data: ApplicationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    """Partially update an existing job application owned by the authenticated user."""
    record = await update_user_application(db, application_id, current_user.id, data)
    return ApplicationResponse.model_validate(record)


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tracked job application",
)
async def delete_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a job application record owned by the authenticated user."""
    await delete_user_application(db, application_id, current_user.id)
