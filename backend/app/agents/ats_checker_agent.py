"""LangGraph orchestrator for public ATS CV grading."""

import asyncio
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents.node.ats_grading_node import grade_cv_node, parse_cv_node
from app.agents.node.pdf_extract_node import extract_ats_pdf_text_node
from app.schemas.ats_checker import ATSCheckResult, ParsedCVDocument


class ATSCheckerState(TypedDict):
    file_bytes: bytes
    target_role: str | None
    raw_text: str
    parsed_cv: ParsedCVDocument | None
    result: ATSCheckResult | None
    error: str | None


def parse_router(state: ATSCheckerState) -> str:
    """Route to CV parser node only if text extraction succeeded."""
    if state.get("error") or not state.get("raw_text"):
        return END
    return "parse_cv"


def grade_router(state: ATSCheckerState) -> str:
    """Route to grading node only if structured CV parsing succeeded."""
    if state.get("error") or state.get("parsed_cv") is None:
        return END
    return "grade_cv"


workflow = StateGraph(ATSCheckerState)
workflow.add_node("extract_text", extract_ats_pdf_text_node)
workflow.add_node("parse_cv", parse_cv_node)
workflow.add_node("grade_cv", grade_cv_node)

workflow.set_entry_point("extract_text")
workflow.add_conditional_edges(
    "extract_text", parse_router, {"parse_cv": "parse_cv", END: END}
)
workflow.add_conditional_edges(
    "parse_cv", grade_router, {"grade_cv": "grade_cv", END: END}
)
workflow.add_edge("grade_cv", END)

ats_checker_app = workflow.compile()


async def check_cv_ats(file_bytes: bytes, target_role: str | None = None) -> dict:
    """Run the ATS checker graph on raw PDF bytes (in-memory, no disk I/O)."""
    initial_state: ATSCheckerState = {
        "file_bytes": file_bytes,
        "target_role": target_role.strip() if target_role and target_role.strip() else None,
        "raw_text": "",
        "parsed_cv": None,
        "result": None,
        "error": None,
    }

    final_state = await asyncio.to_thread(ats_checker_app.invoke, initial_state)

    return {
        "result": final_state.get("result"),
        "error": final_state.get("error"),
    }


__all__ = ["ATSCheckerState", "ats_checker_app", "check_cv_ats", "workflow"]
