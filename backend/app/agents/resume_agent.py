"""LangGraph orchestrator for resume PDF parsing into user profiles."""

import asyncio
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents.node.pdf_extract_node import extract_resume_pdf_text_node
from app.agents.node.resume_parsing_node import parse_with_llm_node
from app.schemas.profile import ResumeProfile


class ResumeState(TypedDict):
    file_path: str
    raw_text: str
    parsed_profile: ResumeProfile | None
    error: str | None


def router(state: ResumeState) -> str:
    """Route to LLM parsing only if PDF text extraction succeeded."""
    if state.get("error") or not state.get("raw_text"):
        return END
    return "parse_with_llm"


workflow = StateGraph(ResumeState)
workflow.add_node("extract_text", extract_resume_pdf_text_node)
workflow.add_node("parse_with_llm", parse_with_llm_node)

workflow.set_entry_point("extract_text")
workflow.add_conditional_edges(
    "extract_text", router, {"parse_with_llm": "parse_with_llm", END: END}
)
workflow.add_edge("parse_with_llm", END)

resume_parser_app = workflow.compile()


async def process_resume(file_path: str) -> dict:
    """Run the resume parsing workflow off the event loop and return the result."""
    initial_state: ResumeState = {
        "file_path": file_path,
        "raw_text": "",
        "parsed_profile": None,
        "error": None,
    }

    final_state = await asyncio.to_thread(resume_parser_app.invoke, initial_state)

    return {
        "raw_text": final_state.get("raw_text"),
        "profile": final_state.get("parsed_profile"),
        "error": final_state.get("error"),
    }


__all__ = ["ResumeState", "process_resume", "resume_parser_app", "workflow"]
