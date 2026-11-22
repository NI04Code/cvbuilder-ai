"""Public ATS Checker API endpoint — HTTP upload validation delegating to ats_checker_service."""

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status

from app.schemas.ats_checker import ATSCheckResult
from app.security.rate_limiter import limiter
from app.security.sanitizer import is_pdf_magic_bytes, sanitize_text
from app.services.ats_checker_service import analyze_cv_pdf

router = APIRouter(prefix="/ats-checker", tags=["ATS Checker"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post(
    "/analyze",
    response_model=ATSCheckResult,
    summary="Analyze a CV for ATS compatibility (public, no login required)",
)
@limiter.limit("3/minute")
async def analyze_cv(
    request: Request,
    file: UploadFile = File(...),
    target_role: str | None = Form(default=None),
    company_name: str | None = Form(default=None),
    job_description: str | None = Form(default=None),
) -> ATSCheckResult:
    """
    Upload a PDF resume/CV and receive a detailed ATS compatibility report.

    This endpoint is public and does not require authentication.
    The uploaded file is processed entirely in memory and is NOT stored anywhere.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF files are accepted.",
        )

    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )
    if not is_pdf_magic_bytes(file_bytes):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file content. Only valid PDF files are accepted.",
        )

    clean_role = sanitize_text(target_role)[:120] if target_role else None
    clean_company = sanitize_text(company_name)[:120] if company_name else None
    clean_jd = sanitize_text(job_description)[:2500] if job_description else None

    return await analyze_cv_pdf(
        file_bytes,
        target_role=clean_role or None,
        company_name=clean_company or None,
        job_description=clean_jd or None,
    )
