"""Cold email generation node."""

import logging
import re
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.helper.llm_factory import get_structured_llm
from app.schemas.cold_email import ColdEmailContent, ColdEmailGenerateRequest
from app.schemas.cv import JobRequirements
from app.schemas.profile import ProfileResponse

logger = logging.getLogger(__name__)


class ColdEmailNodeState(TypedDict, total=False):
    profile: ProfileResponse
    request: ColdEmailGenerateRequest
    fallback_name: str | None
    job_requirements: JobRequirements | None
    cold_email: ColdEmailContent | None
    error: str | None


def _normalize_cold_email_text(text: str) -> str:
    """Clean carriage returns, accidental markdown emphasis, and excessive blank lines."""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def generate_cold_email_node(state: ColdEmailNodeState) -> dict:
    """Generate a concise, hook-driven recruiter cold email grounded in profile and job context."""
    logger.info("Generating Tailored Cold Email")
    structured_llm = get_structured_llm(ColdEmailContent, temperature=0.3)

    reqs = state.get("job_requirements")
    profile = state["profile"]
    request = state["request"]

    target_job = request.job_title or (reqs.job_title if reqs else None) or "the open role"
    target_company = request.company_name or (reqs.company if reqs else None) or "your team"
    recruiter_name = (request.recruiter_name or "").strip()
    greeting_rule = (
        f"Address the recruiter directly as 'Hi {recruiter_name},' (or 'Hello {recruiter_name},')."
        if recruiter_name
        else "Use a brief natural greeting like 'Hi there,' or 'Hi Hiring Team,'."
    )
    candidate_name = (
        (profile.personal_info.name if profile.personal_info else None)
        or state.get("fallback_name")
        or "Candidate"
    )

    system_prompt = (
        f"Write a concise, high-reply-rate cold outreach email to a recruiter for '{target_job}' at '{target_company}'.\n"
        "RULES:\n"
        "1. Subject Line (`subject`): Short (<= 9 words), specific, and value-first (mention a relevant metric, domain match, or the role — avoid clickbait or generic 'Job Application').\n"
        "2. Opening Hook: Start immediately after the greeting with a sharp 1-2 sentence hook connecting a concrete priority/challenge from JOB to the candidate's strongest matching win/metric from PROFILE (never start with 'I hope this email finds you well' or 'My name is...').\n"
        "3. Conciseness: Keep `email_body` strictly 90-150 words total across 3 short scannable paragraphs (hook + proof, quick relevance bridge, 1-sentence low-friction CTA asking for a brief chat).\n"
        f"4. Greeting & Sign-off: {greeting_rule} Plain text only (no Markdown or bullets). End with 'Best,\\n{candidate_name}'.\n"
        "5. Integrity: Use ONLY facts, roles, skills, and metrics present in PROFILE; never invent anything."
    )

    human_content = (
        f"RECRUITER:{recruiter_name or 'Not provided'}\n"
        f"PROFILE:{profile.model_dump_json(exclude_none=True)}\n"
        f"JOB:{reqs.model_dump_json(exclude_none=True) if reqs else '{}'}"
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_content),
    ]

    try:
        output = structured_llm.invoke(messages)
        normalized = output.model_copy(
            update={
                "subject": _normalize_cold_email_text(output.subject),
                "email_body": _normalize_cold_email_text(output.email_body),
            }
        )
        return {**state, "cold_email": normalized}
    except Exception as e:
        logger.error(f"Error generating cold email: {e}")
        return {**state, "error": f"Failed to generate cold email: {str(e)}"}
