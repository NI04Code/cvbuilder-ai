import asyncio
import logging
import re
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from app.agents.cv_agent import analyze_job_node
from app.agents.llm import get_structured_llm
from app.schemas.cover_letter import CoverLetterContent, CoverLetterGenerateRequest
from app.schemas.cv import JobRequirements
from app.schemas.profile import ProfileResponse

logger = logging.getLogger(__name__)


class CoverLetterState(TypedDict):
    profile: ProfileResponse
    request: CoverLetterGenerateRequest
    fallback_name: str | None
    job_requirements: JobRequirements | None
    cover_letter: CoverLetterContent | None
    error: str | None


def _normalize_cover_letter_text(text: str) -> str:
    """Clean carriage returns, accidental markdown emphasis, and excessive blank lines."""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def generate_cover_letter_node(state: CoverLetterState) -> CoverLetterState:
    """Generates a concise, single-page plain-text cover letter from profile and job context."""
    logger.info("Generating Tailored Cover Letter")
    structured_llm = get_structured_llm(CoverLetterContent, temperature=0.25)

    reqs = state["job_requirements"]
    profile = state["profile"]

    target_job = state["request"].job_title or (reqs.job_title if reqs else None) or "the target role"
    target_company = state["request"].company_name or (reqs.company if reqs else None) or "the hiring team"
    candidate_name = (
        (profile.personal_info.name if profile.personal_info else None)
        or state.get("fallback_name")
        or "Candidate"
    )

    system_prompt = (
        f"Write a concise tailored cover letter for '{target_job}' at '{target_company}'.\n"
        "RULES:\n"
        "1. Length: Strictly fit 1 A4 page (200-280 words total, 3-4 short body paragraphs).\n"
        f"2. Format: Plain text only (no Markdown, bullets, or headers). Start with a brief salutation, separate paragraphs with blank lines, and end with 'Sincerely,\\n{candidate_name}'.\n"
        "3. Relevance: Connect the candidate's strongest 2-3 matching experiences, skills, or projects to the role's key requirements.\n"
        "4. Integrity: Use only facts, roles, dates, skills, and metrics present in PROFILE; never invent anything."
    )

    human_content = (
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
            update={"cover_letter_text": _normalize_cover_letter_text(output.cover_letter_text)}
        )
        return {**state, "cover_letter": normalized}
    except Exception as e:
        logger.error(f"Error generating cover letter: {e}")
        return {**state, "error": f"Failed to generate cover letter: {str(e)}"}


def _cover_letter_router(state: CoverLetterState) -> str:
    if state.get("error"):
        return END
    return "generate_cover_letter"


workflow = StateGraph(CoverLetterState)
workflow.add_node("analyze_job", analyze_job_node)
workflow.add_node("generate_cover_letter", generate_cover_letter_node)

workflow.set_entry_point("analyze_job")
workflow.add_conditional_edges(
    "analyze_job",
    _cover_letter_router,
    {"generate_cover_letter": "generate_cover_letter", END: END},
)
workflow.add_edge("generate_cover_letter", END)

cover_letter_app = workflow.compile()


async def process_cover_letter_generation(
    profile: ProfileResponse,
    request: CoverLetterGenerateRequest,
    user_name: str | None = None,
) -> dict:
    """Run the cover letter LangGraph workflow off the event loop and return the result."""
    initial_state: CoverLetterState = {
        "profile": profile,
        "request": request,
        "fallback_name": user_name,
        "job_requirements": None,
        "cover_letter": None,
        "error": None,
    }

    final_state = await asyncio.to_thread(cover_letter_app.invoke, initial_state)
    job_reqs = final_state.get("job_requirements")
    resolved_company = request.company_name or (job_reqs.company if job_reqs else None)

    return {
        "cover_letter": final_state.get("cover_letter"),
        "resolved_company": resolved_company,
        "error": final_state.get("error"),
    }

