"""Public ATS Checker API endpoint — no authentication required."""

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.agents.ats_checker_agent import check_cv_ats
from app.schemas.ats_checker import ATSCheckResult
from app.security.rate_limiter import limiter

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
) -> ATSCheckResult:
    """
    Upload a PDF resume/CV and receive a detailed ATS compatibility report.

    This endpoint is public and does not require authentication.
    The uploaded file is processed entirely in memory and is NOT stored anywhere.
    """
    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF files are accepted.",
        )

    # Read file bytes into memory
    file_bytes = await file.read()

    # Validate file size
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

    # Run ATS analysis (in-memory, no disk write)
    result = await check_cv_ats(file_bytes)

    if result.get("error") or not result.get("result"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error") or "Failed to analyze the CV.",
        )

    return result["result"]
