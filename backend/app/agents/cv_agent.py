"""LangGraph orchestrator for tailored CV generation."""

import asyncio
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents.node.cv_generation_node import (
    _enforce_single_row_skills,
    generate_cv_node,
    score_cv_node,
)
from app.agents.node.job_analysis_node import analyze_job_node
from app.schemas.cv import CVGenerateRequest, JobRequirements, TailoredCV
from app.schemas.profile import ProfileResponse


class CVState(TypedDict):
    profile: ProfileResponse
    request: CVGenerateRequest
    fallback_name: str | None
    job_requirements: JobRequirements | None
    tailored_cv: TailoredCV | None
    error: str | None


def router(state: CVState) -> str:
    if state.get("error"):
        return END
    return "generate_cv"


def score_router(state: CVState) -> str:
    if state.get("error") or not state.get("tailored_cv"):
        return END
    return "score_cv"


workflow = StateGraph(CVState)
workflow.add_node("analyze_job", analyze_job_node)
workflow.add_node("generate_cv", generate_cv_node)
workflow.add_node("score_cv", score_cv_node)

workflow.set_entry_point("analyze_job")
workflow.add_conditional_edges("analyze_job", router, {"generate_cv": "generate_cv", END: END})
workflow.add_conditional_edges("generate_cv", score_router, {"score_cv": "score_cv", END: END})
workflow.add_edge("score_cv", END)

cv_generator_app = workflow.compile()


async def process_cv_generation(
    profile: ProfileResponse,
    request: CVGenerateRequest,
    user_name: str | None = None,
) -> dict:
    """Run the tailored CV workflow off the event loop and return the result."""
    initial_state: CVState = {
        "profile": profile,
        "request": request,
        "fallback_name": user_name,
        "job_requirements": None,
        "tailored_cv": None,
        "error": None,
    }

    final_state = await asyncio.to_thread(cv_generator_app.invoke, initial_state)
    job_reqs = final_state.get("job_requirements")
    resolved_company = request.company_name or (job_reqs.company if job_reqs else None)

    return {
        "tailored_cv": final_state.get("tailored_cv"),
        "resolved_company": resolved_company,
        "error": final_state.get("error"),
    }


__all__ = [
    "CVState",
    "_enforce_single_row_skills",
    "cv_generator_app",
    "process_cv_generation",
    "workflow",
]
