"""Shared job description analysis node used by CV, Cover Letter, and future job-targeted agents."""

import logging
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.helper.llm_factory import get_structured_llm
from app.schemas.cv import JOB_DESCRIPTION_MAX_LENGTH, JobRequirements
from app.schemas.document import JobTargetedRequest

logger = logging.getLogger(__name__)


class JobAnalysisState(TypedDict, total=False):
    request: JobTargetedRequest
    job_requirements: JobRequirements | None
    error: str | None


def analyze_job_node(state: JobAnalysisState) -> dict:
    """Extract structured job requirements, skills, and ATS keywords from a job description."""
    logger.info("Analyzing Job Description")
    structured_llm = get_structured_llm(JobRequirements, temperature=0)

    persona = (
        "Extract structured requirements, required/preferred skills, responsibilities, "
        "education, and ATS keywords from the job description."
    )

    request = state["request"]
    bounded_jd = request.job_description.strip()[:JOB_DESCRIPTION_MAX_LENGTH]
    prompt = (
        f"Job Title: {request.job_title or 'Not specified'}\n"
        f"Company Name: {request.company_name or 'Not specified'}\n"
        f"Job Description:\n\n{bounded_jd}"
    )

    messages = [
        SystemMessage(content=persona),
        HumanMessage(content=prompt),
    ]

    try:
        job_reqs = structured_llm.invoke(messages)
        return {**state, "job_requirements": job_reqs}
    except Exception as e:
        logger.error(f"Error analyzing job description: {e}")
        return {**state, "error": f"Failed to analyze job description: {str(e)}"}

