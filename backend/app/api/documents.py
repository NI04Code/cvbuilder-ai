"""Unified metadata-tagged document history endpoint — HTTP layer delegating to document_service."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.document import DocumentHistoryItem, DocumentType
from app.security.jwt import get_current_user
from app.services.document_service import list_unified_documents

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
    limit: int = Query(50, ge=1, le=100, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentHistoryItem]:
    """Return user-owned CVs and/or cover letters tagged with `document_type` sorted newest-first."""
    return await list_unified_documents(
        db,
        current_user.id,
        document_type=document_type,
        limit=limit,
        offset=offset,
    )
