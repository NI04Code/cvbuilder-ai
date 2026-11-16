"""LangGraph orchestrator for concise single-page cover letter generation."""

import asyncio
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents.node.cover_letter_generation_node import (
    _normalize_cover_letter_text,
    generate_cover_letter_node,
)
from app.agents.node.job_analysis_node import analyze_job_node
from app.schemas.cover_letter import CoverLetterContent, CoverLetterGenerateRequest
from app.schemas.cv import JobRequirements
from app.schemas.profile import ProfileResponse


class CoverLetterState(TypedDict):
    profile: ProfileResponse
    request: CoverLetterGenerateRequest
    fallback_name: str | None
    job_requirements: JobRequirements | None
    cover_letter: CoverLetterContent | None
    error: str | None


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


__all__ = [
    "CoverLetterState",
    "_normalize_cover_letter_text",
    "cover_letter_app",
    "process_cover_letter_generation",
    "workflow",
]
