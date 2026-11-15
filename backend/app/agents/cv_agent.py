import asyncio
import logging
from pathlib import Path
import re
from typing import TypedDict

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
import pymupdf

from app.agents.ats_rubric import grade_parsed_cv
from app.agents.llm import get_structured_llm
from app.config import settings
from app.schemas.ats_checker import ParsedCVDocument
from app.schemas.profile import ProfileResponse
from app.schemas.cv import (
    CVGenerateRequest,
    JOB_DESCRIPTION_MAX_LENGTH,
    JobRequirements,
    SkillCategory,
    TailoredCV,
)

logger = logging.getLogger(__name__)

# Maximum single-line width in points on A4 (595.28pt - 2 * 57.6pt margin = 480.08pt usable)
_MAX_SKILL_ROW_WIDTH_PT = 472.0
_CALIBRI_REGULAR = Path("C:/Windows/Fonts/calibri.ttf")
_CALIBRI_BOLD = Path("C:/Windows/Fonts/calibrib.ttf")


def _get_measurement_fonts() -> tuple[pymupdf.Font, pymupdf.Font]:
    """Return regular and bold fonts (Calibri when available, else Helvetica) for 1-row width checks."""
    if _CALIBRI_REGULAR.exists() and _CALIBRI_BOLD.exists():
        return (
            pymupdf.Font(fontfile=str(_CALIBRI_REGULAR)),
            pymupdf.Font(fontfile=str(_CALIBRI_BOLD)),
        )
    return pymupdf.Font("helv"), pymupdf.Font("hebo")


def _collect_non_skill_cv_text(cv: TailoredCV) -> str:
    """Concatenate all text across non-skill sections of the tailored CV."""
    parts: list[str] = []
    if cv.professional_summary:
        parts.append(cv.professional_summary)
    for exp in cv.work_experiences:
        parts.extend(filter(None, [exp.title, exp.company, exp.location]))
        parts.extend(exp.bullets)
    for edu in cv.education:
        parts.extend(filter(None, [edu.institution, edu.degree, edu.field]))
        parts.extend(edu.relevant_coursework)
    for act in cv.leadership_activities:
        parts.extend(filter(None, [act.title, act.organization, act.location]))
        parts.extend(act.bullets)
    for cert in cv.certifications:
        parts.extend(filter(None, [cert.name, cert.issuer]))
    for proj in cv.projects:
        parts.extend(filter(None, [proj.name, proj.description]))
        parts.extend(proj.technologies)
    return "\n".join(parts)


def _is_skill_mentioned_elsewhere(skill: str, cv_text: str) -> bool:
    """Check whether a skill is already mentioned anywhere in the non-skill sections of the CV."""
    cleaned = skill.strip()
    if not cleaned:
        return False
    pattern = r"(?<![a-zA-Z0-9])" + re.escape(cleaned) + r"(?![a-zA-Z0-9])"
    return bool(re.search(pattern, cv_text, flags=re.IGNORECASE))


def _measure_skill_row_width_pt(
    category: str,
    items: list[str],
    reg_font: pymupdf.Font,
    bold_font: pymupdf.Font,
) -> float:
    """Measure the exact rendered width (in points at 10pt) of '<Category>: item1, item2, ...'."""
    prefix = f"{category.strip()}: "
    body = ", ".join(items)
    return bold_font.text_length(prefix, fontsize=10.0) + reg_font.text_length(body, fontsize=10.0)


def _enforce_single_row_skills(cv: TailoredCV) -> TailoredCV:
    """
    Enforce skill section invariants:
    1. Maximum 3 skill categories.
    2. Each category spans at most 1 row on the CV.
    3. If and only if a category row is full (> 1 row) AND a skill is already mentioned elsewhere
       in the CV, drop that skill (starting from least relevant at the end) until the row fits.
       If the row still overflows after dropping all elsewhere-mentioned skills, trim trailing
       least-relevant skills until it fits on 1 row.
    """
    if not cv.skills:
        return cv

    reg_font, bold_font = _get_measurement_fonts()
    other_text = _collect_non_skill_cv_text(cv)
    curated_categories: list[SkillCategory] = []

    for group in cv.skills[:3]:
        # Deduplicate case-insensitively while preserving relevance order
        seen: set[str] = set()
        items: list[str] = []
        for raw_item in group.items:
            item = raw_item.strip()
            key = item.lower()
            if item and key not in seen:
                seen.add(key)
                items.append(item)

        if not items:
            continue

        category_name = group.category.strip() or "Skills"

        # Only prune when the row is full (exceeds 1 single line)
        if _measure_skill_row_width_pt(category_name, items, reg_font, bold_font) > _MAX_SKILL_ROW_WIDTH_PT:
            # Pass 1: Remove skills from least-relevant to most-relevant IF AND ONLY IF mentioned elsewhere
            idx = len(items) - 1
            while (
                idx >= 0
                and len(items) > 1
                and _measure_skill_row_width_pt(category_name, items, reg_font, bold_font) > _MAX_SKILL_ROW_WIDTH_PT
            ):
                if _is_skill_mentioned_elsewhere(items[idx], other_text):
                    items.pop(idx)
                idx -= 1

            # Pass 2: Hard safety cap if unmentioned skills alone still exceed 1 row
            while (
                len(items) > 1
                and _measure_skill_row_width_pt(category_name, items, reg_font, bold_font) > _MAX_SKILL_ROW_WIDTH_PT
            ):
                items.pop()

        if items:
            curated_categories.append(SkillCategory(category=category_name, items=items))

    cv.skills = curated_categories
    return cv

class CVState(TypedDict):
    profile: ProfileResponse
    request: CVGenerateRequest
    fallback_name: str | None
    job_requirements: JobRequirements | None
    tailored_cv: TailoredCV | None
    error: str | None


def analyze_job_node(state: CVState) -> CVState:
    """Extracts structured requirements from the job description."""
    logger.info("Analyzing Job Description")
    structured_llm = get_structured_llm(JobRequirements, temperature=0)
    
    persona = (
        "Extract structured requirements, required/preferred skills, responsibilities, "
        "education, and ATS keywords from the job description."
    )

    bounded_jd = state["request"].job_description.strip()[:JOB_DESCRIPTION_MAX_LENGTH]
    prompt = (
        f"Job Title: {state['request'].job_title or 'Not specified'}\n"
        f"Company Name: {state['request'].company_name or 'Not specified'}\n"
        f"Job Description:\n\n{bounded_jd}"
    )
    
    messages = [
        SystemMessage(content=persona),
        HumanMessage(content=prompt)
    ]
    
    try:
        job_reqs = structured_llm.invoke(messages)
        return {**state, "job_requirements": job_reqs}
    except Exception as e:
        logger.error(f"Error analyzing job description: {e}")
        return {**state, "error": f"Failed to analyze job description: {str(e)}"}


def generate_cv_node(state: CVState) -> CVState:
    """Generates the tailored CV based on the profile and job requirements."""
    logger.info("Generating Tailored CV")
    structured_llm = get_structured_llm(TailoredCV, temperature=0.1)
    
    reqs = state["job_requirements"]
    profile = state["profile"]

    target_job = state["request"].job_title or (reqs.job_title if reqs else None) or "the target role"
    target_company = state["request"].company_name or (reqs.company if reqs else None) or "the target company"

    system_prompt = (
        f"Tailor the candidate's resume into a `TailoredCV` for '{target_job}' at '{target_company}'.\n\n"
        "RULES:\n"
        "1. Length: Target 1 A4 page best-effort, max 2 pages. Never cut strong relevant experience, certs, or projects just for 1 page; trim/omit `professional_summary` first if tight.\n"
        "2. Experience: Keep transferable roles (e.g. cloud, DevOps, data, Docker/K8s) and 2-4 high-impact bullets per role using existing metrics and strong action verbs; only drop unrelated filler.\n"
        "3. `section_order`: Keep ['summary', <experience/education>, 'leadership', 'certifications', 'projects', 'skills']—ONLY swap 'experience' and 'education'.\n"
        "4. Sections: `work_experiences` & `education` are required. Include optional sections only when profile has relevant data; otherwise use null or [].\n"
        "5. `skills`: Group into <=3 concise categories, rank items most-to-least relevant, max 1 row per category (~<=90 chars). Only drop an elsewhere-mentioned skill if its row would wrap.\n"
        "6. Integrity: Never fabricate facts or metrics. Use '-' instead of '()' in titles (e.g. 'Software Engineer - DevOps'). Populate `keywords_matched` and estimate `ats_score` (0-100)."
    )

    human_content = (
        f"PROFILE:{profile.model_dump_json(exclude_none=True)}\n"
        f"JOB:{reqs.model_dump_json(exclude_none=True) if reqs else '{}'}"
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_content)
    ]
    
    try:
        tailored_cv = structured_llm.invoke(messages)
        tailored_cv = _enforce_single_row_skills(tailored_cv)
        return {**state, "tailored_cv": tailored_cv}
    except Exception as e:
        logger.error(f"Error generating CV: {e}")
        return {**state, "error": f"Failed to generate CV: {str(e)}"}


def score_cv_node(state: CVState) -> CVState:
    """Grade the generated CV with the exact same structured ParsedCVDocument pipeline used by the ATS checker."""
    tailored_cv = state.get("tailored_cv")
    if not tailored_cv:
        return state

    try:
        parsed_doc = ParsedCVDocument.from_tailored_cv(
            tailored_cv,
            state["profile"].personal_info,
            fallback_name=state.get("fallback_name"),
        )
        reqs = state.get("job_requirements")
        target_job = state["request"].job_title or (reqs.job_title if reqs else None)
        ats_result = grade_parsed_cv(parsed_doc, target_role=target_job)
        updated_cv = tailored_cv.model_copy(update={"ats_score": float(ats_result.overall_score)})
        return {**state, "tailored_cv": updated_cv}
    except Exception as e:
        logger.warning(f"Unified ATS scoring fallback to initial score: {e}")
        return state


def router(state: CVState) -> str:
    if state.get("error"):
        return END
    return "generate_cv"


def score_router(state: CVState) -> str:
    if state.get("error") or not state.get("tailored_cv"):
        return END
    return "score_cv"


# Build the Graph
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
    """Helper function to run the graph and return the tailored CV."""
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
