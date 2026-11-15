"""Unified metadata-tagged document history endpoint for the Dashboard."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.cover_letter import GeneratedCoverLetter
from app.models.generated_cv import GeneratedCV
from app.models.user import User
from app.schemas.document import DocumentHistoryItem, DocumentType
from app.security.jwt import get_current_user

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get(
    "/history",
    response_model=list[DocumentHistoryItem],
    summary="List generated CVs and cover letters tagged with document_type metadata",
)
async def list_generated_documents(
    document_type: DocumentType | None = Query(
        None,
        description="Optional filter: 'cv' or 'cover_letter'. Omit to return both.",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentHistoryItem]:
    """Return user-owned CVs and/or cover letters tagged with `document_type` sorted newest-first."""
    items: list[DocumentHistoryItem] = []

    if document_type in (None, "cv"):
        cv_result = await db.execute(
            select(GeneratedCV)
            .where(GeneratedCV.user_id == current_user.id)
            .order_by(GeneratedCV.created_at.desc())
        )
        for cv in cv_result.scalars().all():
            items.append(
                DocumentHistoryItem(
                    id=cv.id,
                    document_type="cv",
                    job_title=cv.job_title,
                    company_name=cv.company_name,
                    ats_score=cv.ats_score,
                    created_at=cv.created_at,
                )
            )

    if document_type in (None, "cover_letter"):
        cl_result = await db.execute(
            select(GeneratedCoverLetter)
            .where(GeneratedCoverLetter.user_id == current_user.id)
            .order_by(GeneratedCoverLetter.created_at.desc())
        )
        for cl in cl_result.scalars().all():
            items.append(
                DocumentHistoryItem(
                    id=cl.id,
                    document_type="cover_letter",
                    job_title=cl.job_title,
                    company_name=cl.company_name,
                    ats_score=None,
                    created_at=cl.created_at,
                )
            )

    items.sort(key=lambda item: item.created_at, reverse=True)
    return items

