"""Nodes for parsing uploaded CV text into structured JSON and grading it against the ATS rubric."""

import logging
from typing import TypedDict

from app.agents.helper.ats_rubric import grade_parsed_cv, parse_cv_to_structured
from app.schemas.ats_checker import ATSCheckResult, ParsedCVDocument

logger = logging.getLogger(__name__)


class ATSGradingNodeState(TypedDict, total=False):
    raw_text: str
    target_role: str | None
    parsed_cv: ParsedCVDocument | None
    result: ATSCheckResult | None
    error: str | None


def parse_cv_node(state: ATSGradingNodeState) -> dict:
    """Parse raw PDF text into the structured ParsedCVDocument schema (null/[] for missing fields)."""
    logger.info("ATS Checker: parsing CV text into structured ParsedCVDocument JSON")
    try:
        parsed_cv = parse_cv_to_structured(state["raw_text"])
        return {**state, "parsed_cv": parsed_cv}
    except Exception as e:
        logger.error(f"ATS Checker: structured CV parsing failed — {e}")
        return {**state, "error": f"Failed to parse CV structure: {str(e)}"}


def grade_cv_node(state: ATSGradingNodeState) -> dict:
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

