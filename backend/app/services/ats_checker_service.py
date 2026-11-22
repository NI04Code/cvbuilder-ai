"""ATS CV checking business logic."""

from app.agents.ats_checker_agent import check_cv_ats
from app.core.exceptions import GenerationError
from app.schemas.ats_checker import ATSCheckResult


async def analyze_cv_pdf(
    file_bytes: bytes,
    target_role: str | None = None,
    company_name: str | None = None,
    job_description: str | None = None,
) -> ATSCheckResult:
    """Run in-memory ATS compatibility analysis on validated PDF bytes."""
    result = await check_cv_ats(
        file_bytes,
        target_role=target_role,
        company_name=company_name,
        job_description=job_description,
    )
    if result.get("error") or not result.get("result"):
        raise GenerationError(result.get("error") or "Failed to analyze the CV.")
    return result["result"]
