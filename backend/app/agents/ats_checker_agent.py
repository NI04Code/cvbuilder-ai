"""LangGraph agent for public ATS CV grading.

Processes PDF bytes in memory (no disk I/O) and produces a structured
ATSCheckResult with adaptive, career-level-aware scoring.
"""

import logging
from typing import TypedDict

import fitz  # PyMuPDF
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph

from app.config import settings
from app.schemas.ats_checker import ATSCheckResult

logger = logging.getLogger(__name__)


# ── State Definition ──────────────────────────────────────────────────────


class ATSCheckerState(TypedDict):
    file_bytes: bytes
    raw_text: str
    result: ATSCheckResult | None
    error: str | None


# ── Graph Nodes ───────────────────────────────────────────────────────────


def extract_text_node(state: ATSCheckerState) -> ATSCheckerState:
    """Extract text from PDF bytes in memory — no file written to disk."""
    logger.info("ATS Checker: extracting text from uploaded PDF bytes")
    text = ""
    try:
        with fitz.open(stream=state["file_bytes"], filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()

        if not text.strip():
            return {**state, "error": "Could not extract any text from the PDF. The file may be image-based or corrupted."}

        return {**state, "raw_text": text}
    except Exception as e:
        logger.error(f"ATS Checker: text extraction failed — {e}")
        return {**state, "error": f"Failed to read PDF: {str(e)}"}


def grade_cv_node(state: ATSCheckerState) -> ATSCheckerState:
    """Grade the CV text using Gemini with a detailed adaptive rubric."""
    logger.info("ATS Checker: grading CV with Gemini")

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        google_api_key=settings.google_api_key,
    )
    structured_llm = llm.with_structured_output(ATSCheckResult)

    system_prompt = """\
You are an expert Applicant Tracking System (ATS) analyst and career advisor.
Your task is to grade a candidate's CV/resume for ATS compatibility.

CRITICAL RULES FOR ADAPTIVE SCORING:

1. DETECT THE CANDIDATE'S CAREER LEVEL first (Entry-Level, Mid-Level, Senior, Executive) based on their years of experience, job titles, and education.

2. DYNAMICALLY IDENTIFY which sections are present in the CV. Common sections include:
   - Contact Information
   - Professional Summary / Objective
   - Work Experience
   - Education
   - Skills (Technical / Soft)
   - Certifications
   - Projects
   - Awards / Publications

3. DO NOT PENALIZE missing optional sections when the candidate's level justifies it:
   - Senior/Executive candidates with extensive work experience do NOT need a Professional Summary — their track record speaks for itself.
   - Entry-level candidates WITHOUT work experience SHOULD have a Professional Summary or Objective.
   - Senior candidates do NOT need a Projects section if their work experience is substantial.
   - Entry-level candidates BENEFIT from Projects and Certifications to compensate for limited experience.

4. ASSIGN DYNAMIC WEIGHTS to each section based on what is present and the candidate's career level. Weights MUST sum to 1.0. Example weighting strategies:
   - Senior candidate: Work Experience 0.40, Skills 0.20, Contact Info 0.10, Education 0.10, Formatting 0.20
   - Entry-level candidate: Education 0.20, Skills 0.20, Projects 0.15, Summary 0.15, Contact Info 0.10, Formatting 0.20

5. SCORING GUIDELINES per section (apply consistently):
   - Contact Information: 100 if name + email + phone + LinkedIn present. Deduct points for missing items.
   - Work Experience: Score based on quantified achievements (numbers, percentages, dollar amounts), action verbs, relevance, and chronological clarity.
   - Education: Score based on degree relevance, institution mention, dates, and GPA/honors if entry-level.
   - Skills: Score based on proper categorization, relevance to apparent field, and ATS-parseable format (no graphics/bars).
   - Formatting: Score based on single-column layout, standard section headings, no tables/images/charts, consistent date formats, parseable by ATS software.

6. The overall_score MUST equal the weighted average of all section scores using the weights you assigned.

7. Be constructive and specific in your feedback. Every suggestion must be actionable.

8. For keyword analysis, identify the candidate's apparent industry/field and evaluate keywords against that context — do not suggest unrelated keywords.

9. Be consistent: the same CV must always receive the same scores."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"CV/Resume Text:\n\n{state['raw_text']}"),
    ]

    try:
        result = structured_llm.invoke(messages)
        return {**state, "result": result}
    except Exception as e:
        logger.error(f"ATS Checker: grading failed — {e}")
        return {**state, "error": f"Failed to grade CV: {str(e)}"}


# ── Router ────────────────────────────────────────────────────────────────


def router(state: ATSCheckerState) -> str:
    """Route to grading node only if text extraction succeeded."""
    if state.get("error"):
        return END
    if not state.get("raw_text"):
        return END
    return "grade_cv"


# ── Build the Graph ───────────────────────────────────────────────────────

workflow = StateGraph(ATSCheckerState)

workflow.add_node("extract_text", extract_text_node)
workflow.add_node("grade_cv", grade_cv_node)

workflow.set_entry_point("extract_text")
workflow.add_conditional_edges(
    "extract_text", router, {"grade_cv": "grade_cv", END: END}
)
workflow.add_edge("grade_cv", END)

ats_checker_app = workflow.compile()


# ── Public Helper ─────────────────────────────────────────────────────────


async def check_cv_ats(file_bytes: bytes) -> dict:
    """Run the ATS checker graph on raw PDF bytes (in-memory, no disk I/O).

    Returns:
        dict with keys "result" (ATSCheckResult | None) and "error" (str | None).
    """
    initial_state: ATSCheckerState = {
        "file_bytes": file_bytes,
        "raw_text": "",
        "result": None,
        "error": None,
    }

    final_state = ats_checker_app.invoke(initial_state)

    return {
        "result": final_state.get("result"),
        "error": final_state.get("error"),
    }
