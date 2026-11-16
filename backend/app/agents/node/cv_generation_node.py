"""Nodes for generating and grading tailored CVs."""

import logging
from pathlib import Path
import re
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
import pymupdf

from app.agents.helper.ats_rubric import grade_parsed_cv
from app.agents.helper.llm_factory import get_structured_llm
from app.schemas.ats_checker import ParsedCVDocument
from app.schemas.cv import JobRequirements, SkillCategory, TailoredCV
from app.schemas.document import JobTargetedRequest
from app.schemas.profile import ProfileResponse

logger = logging.getLogger(__name__)

# Maximum single-line width in points on A4 (595.28pt - 2 * 57.6pt margin = 480.08pt usable)
_MAX_SKILL_ROW_WIDTH_PT = 472.0
_CALIBRI_REGULAR = Path("C:/Windows/Fonts/calibri.ttf")
_CALIBRI_BOLD = Path("C:/Windows/Fonts/calibrib.ttf")


class CVNodeState(TypedDict, total=False):
    profile: ProfileResponse
    request: JobTargetedRequest
    fallback_name: str | None
    job_requirements: JobRequirements | None
    tailored_cv: TailoredCV | None
    error: str | None


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
    """Enforce <= 3 skill categories, each fitting on at most 1 A4 row."""
    if not cv.skills:
        return cv

    reg_font, bold_font = _get_measurement_fonts()
    other_text = _collect_non_skill_cv_text(cv)
    curated_categories: list[SkillCategory] = []

    for group in cv.skills[:3]:
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

        if _measure_skill_row_width_pt(category_name, items, reg_font, bold_font) > _MAX_SKILL_ROW_WIDTH_PT:
            idx = len(items) - 1
            while (
                idx >= 0
                and len(items) > 1
                and _measure_skill_row_width_pt(category_name, items, reg_font, bold_font) > _MAX_SKILL_ROW_WIDTH_PT
            ):
                if _is_skill_mentioned_elsewhere(items[idx], other_text):
                    items.pop(idx)
                idx -= 1

            while (
                len(items) > 1
                and _measure_skill_row_width_pt(category_name, items, reg_font, bold_font) > _MAX_SKILL_ROW_WIDTH_PT
            ):
                items.pop()

        if items:
            curated_categories.append(SkillCategory(category=category_name, items=items))

    cv.skills = curated_categories
    return cv


def generate_cv_node(state: CVNodeState) -> dict:
    """Generate a structured tailored CV from the user profile and job requirements."""
    logger.info("Generating Tailored CV")
    structured_llm = get_structured_llm(TailoredCV, temperature=0.1)

    reqs = state.get("job_requirements")
    profile = state["profile"]
    request = state["request"]

    target_job = request.job_title or (reqs.job_title if reqs else None) or "the target role"
    target_company = request.company_name or (reqs.company if reqs else None) or "the target company"

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
        HumanMessage(content=human_content),
    ]

    try:
        tailored_cv = structured_llm.invoke(messages)
        tailored_cv = _enforce_single_row_skills(tailored_cv)
        return {**state, "tailored_cv": tailored_cv}
    except Exception as e:
        logger.error(f"Error generating CV: {e}")
        return {**state, "error": f"Failed to generate CV: {str(e)}"}


def score_cv_node(state: CVNodeState) -> dict:
    """Grade the generated CV with the unified ATS rubric used by the ATS checker."""
    tailored_cv = state.get("tailored_cv")
    if not tailored_cv:
        return dict(state)

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
        return dict(state)

