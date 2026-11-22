"""LangGraph orchestrator for concise, hook-driven recruiter cold email generation."""

import asyncio
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents.node.cold_email_generation_node import (
    _normalize_cold_email_text,
    generate_cold_email_node,
)
from app.agents.node.job_analysis_node import analyze_job_node
from app.schemas.cold_email import ColdEmailContent, ColdEmailGenerateRequest
from app.schemas.cv import JobRequirements
from app.schemas.profile import ProfileResponse


class ColdEmailState(TypedDict):
    profile: ProfileResponse
    request: ColdEmailGenerateRequest
    fallback_name: str | None
    job_requirements: JobRequirements | None
    cold_email: ColdEmailContent | None
    error: str | None


def _cold_email_router(state: ColdEmailState) -> str:
    if state.get("error"):
        return END
    return "generate_cold_email"


workflow = StateGraph(ColdEmailState)
workflow.add_node("analyze_job", analyze_job_node)
workflow.add_node("generate_cold_email", generate_cold_email_node)

workflow.set_entry_point("analyze_job")
workflow.add_conditional_edges(
    "analyze_job",
    _cold_email_router,
    {"generate_cold_email": "generate_cold_email", END: END},
)
workflow.add_edge("generate_cold_email", END)

cold_email_app = workflow.compile()


async def process_cold_email_generation(
    profile: ProfileResponse,
    request: ColdEmailGenerateRequest,
    user_name: str | None = None,
) -> dict:
    """Run the cold email LangGraph workflow off the event loop and return the result."""
    initial_state: ColdEmailState = {
        "profile": profile,
        "request": request,
        "fallback_name": user_name,
        "job_requirements": None,
        "cold_email": None,
        "error": None,
    }

    final_state = await asyncio.to_thread(cold_email_app.invoke, initial_state)
    job_reqs = final_state.get("job_requirements")
    resolved_company = request.company_name or (job_reqs.company if job_reqs else None)

    return {
        "cold_email": final_state.get("cold_email"),
        "resolved_company": resolved_company,
        "error": final_state.get("error"),
    }


__all__ = [
    "ColdEmailState",
    "_normalize_cold_email_text",
    "cold_email_app",
    "process_cold_email_generation",
    "workflow",
]
