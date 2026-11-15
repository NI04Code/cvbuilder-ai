"""LangGraph agent for public ATS CV grading.

Processes PDF bytes in memory (no disk I/O), parses extracted text into the
canonical `ParsedCVDocument` (`TailoredCV` + `PersonalInfo` JSON) schema, and
produces a structured `ATSCheckResult` using the unified ATS rubric.
"""

import asyncio
import logging
from typing import TypedDict

import pymupdf as fitz  # PyMuPDF
from langgraph.graph import END, StateGraph

from app.agents.ats_rubric import grade_parsed_cv, parse_cv_to_structured
from app.schemas.ats_checker import ATSCheckResult, ParsedCVDocument

logger = logging.getLogger(__name__)


# ── State Definition ──────────────────────────────────────────────────────


class ATSCheckerState(TypedDict):
    file_bytes: bytes
    target_role: str | None
    raw_text: str
    parsed_cv: ParsedCVDocument | None
    result: ATSCheckResult | None
    error: str | None


# ── Graph Nodes ───────────────────────────────────────────────────────────


def extract_text_node(state: ATSCheckerState) -> ATSCheckerState:
    """Extract reading-order text from PDF bytes in memory — no file written to disk."""
    logger.info("ATS Checker: extracting text from uploaded PDF bytes")
    text = ""
    try:
        link_uris: list[str] = []
        with fitz.open(stream=state["file_bytes"], filetype="pdf") as doc:
            for page in doc:
                page_text = page.get_text("text", sort=True)
                if page_text:
                    text += page_text.rstrip() + "\n"
                for link in page.get_links():
                    uri = link.get("uri")
                    if isinstance(uri, str) and uri.strip():
                        link_uris.append(uri.strip())

        if not text.strip():
            return {**state, "error": "Could not extract any text from the PDF. The file may be image-based or corrupted."}

        # Preserve hyperlink URIs embedded behind contact labels, project titles, and certifications
        lower_text = text.lower()
        embedded_uris: list[str] = []
        seen_uris: set[str] = set()
        for uri in link_uris:
            lower_uri = uri.lower()
            if not lower_uri.startswith(("http://", "https://")) or lower_uri in seen_uris:
                continue
            seen_uris.add(lower_uri)
            if lower_uri not in lower_text:
                embedded_uris.append(uri)
        if embedded_uris:
            text = f"{text.rstrip()}\nEmbedded Links: {' | '.join(embedded_uris)}"

        return {**state, "raw_text": text}
    except Exception as e:
        logger.error(f"ATS Checker: text extraction failed — {e}")
        return {**state, "error": f"Failed to read PDF: {str(e)}"}


def parse_cv_node(state: ATSCheckerState) -> ATSCheckerState:
    """Parse raw PDF text into the structured ParsedCVDocument schema (null/[] for missing fields)."""
    logger.info("ATS Checker: parsing CV text into structured ParsedCVDocument JSON")
    try:
        parsed_cv = parse_cv_to_structured(state["raw_text"])
        return {**state, "parsed_cv": parsed_cv}
    except Exception as e:
        logger.error(f"ATS Checker: structured CV parsing failed — {e}")
        return {**state, "error": f"Failed to parse CV structure: {str(e)}"}


def grade_cv_node(state: ATSCheckerState) -> ATSCheckerState:
    """Grade the structured ParsedCVDocument using the unified deterministic ATS rubric."""
    logger.info("ATS Checker: grading structured CV JSON with unified ATS rubric")
    parsed_cv = state.get("parsed_cv")
    if parsed_cv is None:
        return {**state, "error": "Failed to grade CV: parsed CV structure is missing."}

    try:
        result = grade_parsed_cv(parsed_cv, target_role=state.get("target_role"))
        return {**state, "result": result}
    except Exception as e:
        logger.error(f"ATS Checker: grading failed — {e}")
        return {**state, "error": f"Failed to grade CV: {str(e)}"}


# ── Routers ───────────────────────────────────────────────────────────────


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


# ── Build the Graph ───────────────────────────────────────────────────────

workflow = StateGraph(ATSCheckerState)

workflow.add_node("extract_text", extract_text_node)
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


# ── Public Helper ─────────────────────────────────────────────────────────


async def check_cv_ats(file_bytes: bytes, target_role: str | None = None) -> dict:
    """Run the ATS checker graph on raw PDF bytes (in-memory, no disk I/O).

    Returns:
        dict with keys "result" (ATSCheckResult | None) and "error" (str | None).
    """
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
