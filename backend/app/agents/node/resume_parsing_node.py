"""Resume LLM parsing node."""

import logging
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.helper.llm_factory import get_structured_llm
from app.schemas.profile import ResumeProfile

logger = logging.getLogger(__name__)


class ResumeParsingNodeState(TypedDict, total=False):
    raw_text: str
    parsed_profile: ResumeProfile | None
    error: str | None


def parse_with_llm_node(state: ResumeParsingNodeState) -> dict:
    """Parse raw resume text into a structured `ResumeProfile` using Gemini."""
    logger.info("Parsing text with Gemini")

    structured_llm = get_structured_llm(ResumeProfile, temperature=0)

    system_prompt = (
        "Extract resume text strictly into the `ResumeProfile` schema; never invent data and leave missing optional fields empty. "
        "Put paid jobs/internships in `work_experiences`, and student clubs, teaching assistantships, or volunteer roles in `leadership_activities`."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Resume Text:\n\n{state['raw_text']}"),
    ]

    try:
        parsed_profile = structured_llm.invoke(messages)
        return {**state, "parsed_profile": parsed_profile}
    except Exception as e:
        logger.error(f"Error parsing with LLM: {e}")
        return {**state, "error": f"Failed to parse resume with AI: {str(e)}"}

