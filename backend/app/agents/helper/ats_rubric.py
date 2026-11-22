"""Shared ATS scoring rubric, deterministic weight normalization, and cached grading helper.

Used by both `ats_checker_agent` (for uploaded PDFs) and `cv_agent` (for newly generated CVs)
so both produce consistent, repeatable ATS scores under identical criteria.
"""

from collections import OrderedDict
import hashlib
import logging
import re
from threading import Lock
import time

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.helper.llm_factory import get_structured_llm
from app.schemas.ats_checker import (
    ATSCheckResult,
    ATSFormattingIssue,
    ATSSectionScore,
    ParsedCVDocument,
)

logger = logging.getLogger(__name__)

_CACHE_MAX_SIZE = 128
_CACHE_TTL_SECONDS = 86_400  # 24 hours
_ATS_CACHE: OrderedDict[str, tuple[float, ATSCheckResult]] = OrderedDict()
_PARSE_CACHE: OrderedDict[str, tuple[float, ParsedCVDocument]] = OrderedDict()
_CACHE_LOCK = Lock()

CV_PARSER_SYSTEM_PROMPT = """\
Parse raw CV text into `ParsedCVDocument`. Follow strictly:
- Factual only: use `null`/`[]` when a section is absent; never invent data.
- `personal_info`: extract name, email, phone, location, LinkedIn -> `linkedin_url`, portfolio/site -> `portfolio_url`, other profile links (`GitHub`, etc.) -> `other_url`.
- `work_experiences` & `leadership_activities`: map each role's full bullets (merge wrapped lines; keep roles aligned even if PDF text blocks are out of order).
- `projects`: merge all project bullets/metrics into `description`; list stack in `technologies`.
- `skills`: preserve named groups (`Category: a, b`) with `skills_are_categorized=true`; for a single flat list set `category="Skills"` and `skills_are_categorized=false`.
- Headings: list all headings in `detected_section_headings`. Set `non_standard_headings=[]` for standard headings/variants (Summary, Experience, Education, Leaderships & Activities, Certifications, Projects, Technical Skills, Additional Information); only flag informal labels (e.g. 'What I Did', 'About Me')."""

ATS_SCORING_RUBRIC = """\
Grade the CV deterministically for ATS compatibility and strict fit against `TARGET ROLE` (or inferred primary role if omitted). Output strict JSON.

1. `candidate_level`: 'Entry-Level' (0-2y/grad/intern), 'Mid-Level' (2-5y), 'Senior' (5-10y), or 'Executive' (10+y/Director/VP/C-level).
2. Sections (canonical names): Always include 'Contact Information', 'Work Experience' (if present or >=Mid-Level), 'Education', 'Skills', 'Formatting'. Include 'Professional Summary' & 'Projects' ONLY if present (or Entry-Level without Work Experience). Include 'Certifications' & 'Leadership & Activity' ONLY if present. OMIT absent optional sections from `sections` entirely (never emit them with score 0).
3. Rubric (0-100 each — judge BOTH completeness AND strict relevance/rigor for `TARGET ROLE`; NEVER excuse role mismatch as strong for another field):
- Contact Information: Name +25, Email +25, Phone +25, Location +12, LinkedIn/GitHub/Portfolio +13.
- Work Experience: Chronology 15, action verbs 15, quantified metrics (>=60%: 30, 40-59%: 20, 15-39%: 10, <15%: 5), `TARGET ROLE` relevance & seniority depth 40 (unrelated field: 0-15/40).
- Education: Institution 20, dates 10, degree/field fit for `TARGET ROLE` 40 (unrelated major: 0-15/40), GPA/coursework/honors relevance (or +30 if >=Mid-Level & matching degree) 30.
- Skills: Categorization (<=3 groups: 25, flat list: 15, wall: 5), `TARGET ROLE` match & depth 60 (unrelated stack: 0-20/60), plain ATS text 15.
- Formatting: Single-column clean text 35, standard headings 25, consistent dates/type 20, concise 1-2 pages 20.
- Professional Summary: `TARGET ROLE` & level alignment (2-4 lines) 50, targeted skills 30, third-person 20.
- Projects: `TARGET ROLE` relevance & outcome 55, relevant tools/stack 25, metrics or URL 20.
- Certifications: `TARGET ROLE` relevance & rigor 75 (unrelated: 0-20, foundational: 40-55, senior/specialist: 65-75), name/issuer/date 25.
- Leadership & Activity: Role/org/dates 40, transferable impact & metrics 60.
4. Compute `overall_score` as weighted average (weights sum to 1.0, prioritizing Work Experience 0.25-0.45, Skills 0.20, Education 0.10-0.20, Formatting 0.10, Contact 0.05).
5. Score-Feedback Consistency & Zero False Positives:
- Qualitative prose only in `summary` & `feedback`: NEVER include numeric scores, %, or 'X/100'.
- NEVER invent missing structural items that contradict `[PRESENT / VERIFIED]`, `[CATEGORIZED]`, `[CONCISE]`, or `[STRONG / VERIFIED]` in `VERIFIED DOCUMENT FACT SHEET` or `PARSED CV JSON`.
- Reserve 95-100 ONLY for genuinely strong, complete, AND directly relevant `TARGET ROLE` fit. Whenever a section scores <95, `feedback` MUST name the specific relevance, rigor, or content gap and `suggestions` MUST list >=1 actionable fix (never write all-positive praise on <95).
- Cite specific CV entries/gaps vs `TARGET ROLE` (no generic filler); keep `formatting_issues: []` when structurally clean."""


_CANONICAL_WEIGHTS: dict[str, dict[str, float]] = {
    "Entry-Level": {
        "experience": 0.25,
        "education": 0.20,
        "skills": 0.20,
        "projects": 0.15,
        "summary": 0.05,
        "contact": 0.05,
        "formatting": 0.10,
        "certifications": 0.05,
        "leadership": 0.05,
    },
    "Mid-Level": {
        "experience": 0.40,
        "skills": 0.20,
        "education": 0.10,
        "projects": 0.10,
        "summary": 0.05,
        "contact": 0.05,
        "formatting": 0.10,
        "certifications": 0.05,
        "leadership": 0.05,
    },
    "Senior": {
        "experience": 0.45,
        "skills": 0.20,
        "education": 0.10,
        "projects": 0.05,
        "summary": 0.05,
        "contact": 0.05,
        "formatting": 0.10,
        "certifications": 0.05,
        "leadership": 0.05,
    },
    "Executive": {
        "experience": 0.45,
        "skills": 0.20,
        "education": 0.10,
        "projects": 0.05,
        "summary": 0.05,
        "contact": 0.05,
        "formatting": 0.10,
        "certifications": 0.05,
        "leadership": 0.05,
    },
}


def _canonical_section_key(section_name: str) -> str:
    """Map free-form LLM section names onto canonical rubric keys."""
    name = section_name.strip().lower()
    if "contact" in name:
        return "contact"
    if "summary" in name or "objective" in name or name in ("profile", "professional profile"):
        return "summary"
    if "experience" in name or "employment" in name:
        return "experience"
    if "education" in name or "academic" in name:
        return "education"
    if "skill" in name or "competenc" in name or "expertise" in name:
        return "skills"
    if "project" in name:
        return "projects"
    if "certif" in name or "license" in name or "credential" in name:
        return "certifications"
    if "leadership" in name or "activity" in name or "activities" in name or "volunteer" in name:
        return "leadership"
    if "format" in name or "layout" in name or "structure" in name or "parse" in name:
        return "formatting"
    return name


def _normalize_level(level: str) -> str:
    """Normalize candidate_level to one of the four canonical rubric levels."""
    lower = level.strip().lower()
    if "entry" in lower or "junior" in lower or "intern" in lower or "grad" in lower:
        return "Entry-Level"
    if "exec" in lower or "director" in lower or "vp" in lower or "chief" in lower:
        return "Executive"
    if "senior" in lower or "lead" in lower or "staff" in lower or "principal" in lower:
        return "Senior"
    return "Mid-Level"


_STANDARD_HEADING_PATTERNS: dict[str, re.Pattern[str]] = {
    "summary": re.compile(
        r"^(?:professional\s+summary|executive\s+summary|career\s+summary|summary|profile|professional\s+profile|career\s+objective|objective)$",
        re.IGNORECASE,
    ),
    "experience": re.compile(
        r"^(?:(?:professional|work|relevant|internship|clinical|teaching|sales|research|legal|finance|accounting|marketing|management|operations|industry)?\s*experience|employment\s+history|work\s+history|career\s+history)$",
        re.IGNORECASE,
    ),
    "education": re.compile(
        r"^(?:education|academic\s+background|education\s*(?:&|and)\s*qualifications|academic\s+qualifications)$",
        re.IGNORECASE,
    ),
    "skills": re.compile(
        r"^(?:technical\s+skills|core\s+skills|clinical\s+skills|professional\s+skills|skills|core\s+competencies|skills\s*(?:&|and)\s*technologies|key\s+skills|technologies\s*(?:&|and)\s*skills|areas\s+of\s+expertise|skills\s*(?:&|and)\s*competencies|technical\s*(?:&|and)\s*clinical\s+skills)$",
        re.IGNORECASE,
    ),
    "projects": re.compile(
        r"^(?:projects|key\s+projects|selected\s+projects|academic\s+projects|personal\s+projects|technical\s+projects|notable\s+projects)$",
        re.IGNORECASE,
    ),
    "certifications": re.compile(
        r"^(?:certifications|licenses\s*(?:&|and)\s*certifications|certifications\s*(?:&|and)\s*licenses|licenses(?:\s*(?:&|and)\s*registrations)?|certificates|professional\s+certifications|certifications\s*(?:&|and)\s*training)$",
        re.IGNORECASE,
    ),
    "leadership": re.compile(
        r"^(?:leadership\s*(?:&|and)\s*activit(?:y|ies)|leadership|activities|extracurricular\s+activities|leadership\s+experience|volunteer\s+experience|volunteering|organizations|community\s+involvement)$",
        re.IGNORECASE,
    ),
}

_NON_STANDARD_HEADING_PATTERN = re.compile(
    r"^(?:what\s+i\s+did|what\s+i've\s+done|my\s+journey|my\s+background|where\s+i\s+studied|where\s+i\s+worked|"
    r"places\s+i\s+worked|about\s+me|who\s+i\s+am|cool\s+stuff|stuff\s+i\s+built|my\s+work|my\s+toolkit|toolbelt|"
    r"superpowers|my\s+story|bio|things\s+i\s+know|stuff\s+i\s+know|tech\s+arsenal)$",
    re.IGNORECASE,
)

_QUANT_UNITS = (
    r"%|x|k|m|b|ms|s|sec|mins?|hrs?|hours?|days?|weeks?|months?|years?|"
    r"users?|clients?|customers?|patients?|beds?|cases?|charts?|shifts?|clinics?|procedures?|consultations?|"
    r"accounts?|invoices?|audits?|budgets?|forecasts?|reports?|transactions?|statements?|filings?|"
    r"subsidiaries|entities|engagements?|portfolios?|assets?|"
    r"hires?|candidates?|employees?|staff|associates?|interns?|interviews?|roles?|positions?|departments?|trainings?|"
    r"campaigns?|impressions?|views?|subscribers?|followers?|leads?|deals?|contracts?|conversions?|launches?|"
    r"branches?|stores?|vendors?|suppliers?|orders?|shipments?|units?|skus?|guests?|rooms?|tickets?|"
    r"classes?|courses?|lectures?|graduates?|pupils?|students?|participants?|essays?|sessions?|labs?|"
    r"requests?|req/s|rps|tps|services?|pipelines?|workflows?|lines?|production\s+lines?|"
    r"nodes?|clusters?|engineers?|developers?|teams?|squads?|person|projects?|endpoints?|apis?|tables?|datasets?|gb|tb|mb|\+"
)

_METRIC_PATTERN = re.compile(
    rf"(?:(?<![A-Za-z0-9]-)(?<![A-Za-z.])\b\d+(?:[.,–-]\d+)?(?:\s+|(?:\s+|-)(?:[A-Za-z][A-Za-z0-9-]*\s+){{0,3}})(?:{_QUANT_UNITS})\b"
    r"|(?:US|AU|CA|SG|HK|NZ)?[$€£¥]\s*\d+|\b(?:IDR|USD|EUR|GBP|SGD|AUD|Rp)\s*\d+(?:[.,]\d+)?\s*[KMB]?"
    r"|\bfrom\s+\d+(?:[.,]\d+)?%?\s+to\s+\d+(?:[.,]\d+)?%?"
    r"|\b\d+\s*/\s*\d+\b|\b\d+\+|\b\d+(?:[.,–-]\d+)?%)",
    re.IGNORECASE,
)


def _extract_section_lines(
    lines: list[str],
    heading_indices: list[tuple[int, str]],
    target_key: str,
) -> list[str]:
    """Return non-empty lines belonging to the first section matching `target_key`."""
    pos = next((i for i, (_, key) in enumerate(heading_indices) if key == target_key), None)
    if pos is None:
        return []
    start_line = heading_indices[pos][0] + 1
    end_line = heading_indices[pos + 1][0] if pos + 1 < len(heading_indices) else len(lines)
    return [line for line in lines[start_line:end_line] if line]


def _count_quantified_bullets(bullets: list[str]) -> tuple[int, int]:
    """Return (quantified_count, quantified_pct) across a list of bullet strings."""
    total = len(bullets)
    if total == 0:
        return 0, 0
    quantified = 0
    for bullet in bullets:
        without_years = re.sub(r"\b(?:199\d|20[0-3]\d)\b", "", bullet)
        if _METRIC_PATTERN.search(without_years):
            quantified += 1
    pct = int(round((quantified / total) * 100))
    return quantified, pct


def extract_cv_facts(normalized_text: str) -> dict[str, object]:
    """Deterministically extract verifiable structural and content facts from CV text."""
    lines = [line.strip() for line in normalized_text.splitlines() if line.strip()]
    top_header = "\n".join(lines[:5])
    word_count = len(normalized_text.split())

    has_email = bool(
        re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", normalized_text)
    )
    header_without_years = re.sub(r"\b(?:19|20)\d{2}\s*[-–]\s*(?:19|20)\d{2}\b", "", top_header)
    phone_candidates = re.findall(r"(?:\+?\d[\d\s().-]{6,}\d)", header_without_years)
    has_phone = any(sum(ch.isdigit() for ch in candidate) >= 8 for candidate in phone_candidates)
    has_linkedin_or_portfolio = bool(
        re.search(
            r"\b(?:linkedin|github|portfolio|gitlab|bitbucket)\b|https?://",
            normalized_text,
            re.IGNORECASE,
        )
    )
    has_location = bool(
        re.search(r"\b[A-Z][a-zA-Z .'-]{1,25},\s*[A-Z][a-zA-Z .'-]{1,25}\b", top_header)
        or re.search(r"\bRemote\b", top_header, re.IGNORECASE)
    )

    detected_headings: dict[str, str] = {}
    non_standard_headings: list[str] = []
    heading_indices: list[tuple[int, str]] = []

    for idx, line in enumerate(lines):
        cleaned = re.sub(r"^[\s•\-*–▪◦#0-9.)]+|[\s:|\-–]+$", "", line).strip()
        if not cleaned or len(cleaned) > 45:
            continue
        matched_canonical: str | None = None
        for key, pattern in _STANDARD_HEADING_PATTERNS.items():
            if pattern.match(cleaned):
                matched_canonical = key
                detected_headings.setdefault(key, cleaned)
                heading_indices.append((idx, key))
                break
        if matched_canonical is None and _NON_STANDARD_HEADING_PATTERN.match(cleaned):
            non_standard_headings.append(cleaned)
            heading_indices.append((idx, f"non_standard:{cleaned}"))

    has_summary = "summary" in detected_headings
    has_experience = "experience" in detected_headings
    has_education = "education" in detected_headings
    has_skills = "skills" in detected_headings
    has_projects = "projects" in detected_headings
    has_certifications = "certifications" in detected_headings
    has_leadership = "leadership" in detected_headings

    uses_standard_headings = (
        (has_experience or has_projects)
        and has_education
        and has_skills
        and len(non_standard_headings) == 0
    )

    # Check if Skills section uses categorized format (Category: item1, item2)
    skills_categorized = False
    skill_category_count = 0
    if has_skills:
        skill_lines = _extract_section_lines(lines, heading_indices, "skills")
        cat_lines = [
            l
            for l in skill_lines
            if re.match(r"^[A-Za-z0-9 &/+_.,()-]{2,40}:\s+\S+", l)
        ]
        if cat_lines and len(cat_lines) >= max(1, int(len(skill_lines) * 0.6)):
            skills_categorized = True
            skill_category_count = len(cat_lines)

    # Scope bullet quantification to Experience (or Leadership if no Experience; fallback to all lines)
    scoped_lines = (
        _extract_section_lines(lines, heading_indices, "experience")
        or _extract_section_lines(lines, heading_indices, "leadership")
        or lines
    )
    bullet_lines = [
        re.sub(r"^[•\-*–▪◦]\s*", "", l).strip()
        for l in scoped_lines
        if re.match(r"^[•\-*–▪◦]\s+\S+", l)
    ]
    action_bullets = [
        b for b in bullet_lines if not b.startswith("[ID:") and len(b.split()) >= 4
    ]
    total_bullets = len(action_bullets)
    quantified_bullets, quantified_pct = _count_quantified_bullets(action_bullets)

    has_gpa_or_coursework = bool(
        re.search(
            r"\b(?:gpa|grade\s+point|relevant\s+coursework|coursework|cum\s+laude|honors|dean'?s\s+list)\b",
            normalized_text,
            re.IGNORECASE,
        )
    )
    is_concise_length = word_count <= 750

    return {
        "word_count": word_count,
        "is_concise_length": is_concise_length,
        "has_email": has_email,
        "has_phone": has_phone,
        "has_location": has_location,
        "has_linkedin_or_portfolio": has_linkedin_or_portfolio,
        "detected_headings": detected_headings,
        "non_standard_headings": non_standard_headings,
        "has_summary": has_summary,
        "has_experience": has_experience,
        "has_education": has_education,
        "has_skills": has_skills,
        "has_projects": has_projects,
        "has_certifications": has_certifications,
        "has_leadership": has_leadership,
        "uses_standard_headings": uses_standard_headings,
        "skills_categorized": skills_categorized,
        "skill_category_count": skill_category_count,
        "total_bullets": total_bullets,
        "quantified_bullets": quantified_bullets,
        "quantified_pct": quantified_pct,
        "has_gpa_or_coursework": has_gpa_or_coursework,
        "searchable_text": normalized_text,
    }


def extract_facts_from_parsed_cv(doc: ParsedCVDocument) -> dict[str, object]:
    """Deterministically extract ground-truth facts from a structured ParsedCVDocument JSON."""
    p = doc.personal_info
    has_email = bool(p and p.email and p.email.strip())
    has_phone = bool(p and p.phone and p.phone.strip())
    has_location = bool(p and p.location and p.location.strip())
    has_linkedin_or_portfolio = bool(
        p
        and (
            (p.linkedin_url and p.linkedin_url.strip())
            or (p.portfolio_url and p.portfolio_url.strip())
            or (p.other_url and p.other_url.strip())
        )
    )

    has_summary = bool(doc.professional_summary and doc.professional_summary.strip())
    has_experience = len(doc.work_experiences) > 0
    has_education = len(doc.education) > 0
    active_skill_cats = [c for c in doc.skills if c.items]
    has_skills = len(active_skill_cats) > 0
    has_projects = len(doc.projects) > 0
    has_certifications = len(doc.certifications) > 0
    has_leadership = len(doc.leadership_activities) > 0

    detected_headings: dict[str, str] = {}
    if has_summary:
        detected_headings["summary"] = "Professional Summary"
    if has_experience:
        detected_headings["experience"] = "Professional Experience"
    if has_education:
        detected_headings["education"] = "Education"
    if has_skills:
        detected_headings["skills"] = "Technical Skills"
    if has_projects:
        detected_headings["projects"] = "Projects"
    if has_certifications:
        detected_headings["certifications"] = "Certifications"
    if has_leadership:
        detected_headings["leadership"] = "Leadership & Activity"

    # Filter non_standard_headings against our strict pattern so standard variants are never flagged
    non_standard_headings: list[str] = []
    for h in doc.non_standard_headings:
        cleaned = re.sub(r"^[\s•\-*–▪◦#0-9.)]+|[\s:|\-–]+$", "", h).strip()
        if not cleaned:
            continue
        if any(pat.match(cleaned) for pat in _STANDARD_HEADING_PATTERNS.values()):
            continue
        if _NON_STANDARD_HEADING_PATTERN.match(cleaned):
            non_standard_headings.append(cleaned)

    uses_standard_headings = (
        (has_experience or has_projects)
        and has_education
        and has_skills
        and len(non_standard_headings) == 0
    )

    skills_categorized = bool(
        has_skills
        and (
            doc.skills_are_categorized
            or len(active_skill_cats) >= 2
            or (
                len(active_skill_cats) == 1
                and active_skill_cats[0].category.strip().lower() not in ("skills", "technical skills")
            )
        )
    )
    skill_category_count = len(active_skill_cats) if skills_categorized else 0

    # Compute quantified bullet ratio directly from structured experience bullets (or leadership if no exp)
    exp_bullets = [b.strip() for exp in doc.work_experiences for b in exp.bullets if b.strip()]
    if not exp_bullets:
        exp_bullets = [b.strip() for act in doc.leadership_activities for b in act.bullets if b.strip()]

    total_bullets = len(exp_bullets)
    quantified_bullets, quantified_pct = _count_quantified_bullets(exp_bullets)

    has_gpa_or_coursework = any(
        bool((edu.gpa and edu.gpa.strip()) or edu.relevant_coursework)
        for edu in doc.education
    )

    # Build searchable text across all structured fields for keyword verification
    text_parts: list[str] = []
    if p:
        text_parts.extend(filter(None, [p.name, p.email, p.phone, p.location, p.linkedin_url, p.portfolio_url, p.other_url]))
    if doc.professional_summary:
        text_parts.append(doc.professional_summary)
    for exp in doc.work_experiences:
        text_parts.extend(filter(None, [exp.title, exp.company, exp.location, exp.start_date, exp.end_date]))
        text_parts.extend(exp.bullets)
    for edu in doc.education:
        text_parts.extend(filter(None, [edu.institution, edu.degree, edu.field, edu.gpa]))
        text_parts.extend(edu.relevant_coursework)
    for act in doc.leadership_activities:
        text_parts.extend(filter(None, [act.title, act.organization, act.location]))
        text_parts.extend(act.bullets)
    for cert in doc.certifications:
        text_parts.extend(filter(None, [cert.name, cert.issuer, cert.date, cert.url]))
    for proj in doc.projects:
        text_parts.extend(filter(None, [proj.name, proj.description, proj.url]))
        text_parts.extend(proj.technologies)
    for cat in active_skill_cats:
        text_parts.append(cat.category)
        text_parts.extend(cat.items)
    text_parts.extend(doc.additional_sections)

    searchable_text = "\n".join(text_parts)
    word_count = doc.word_count if doc.word_count > 0 else len(searchable_text.split())
    is_concise_length = word_count <= 750

    return {
        "word_count": word_count,
        "is_concise_length": is_concise_length,
        "has_email": has_email,
        "has_phone": has_phone,
        "has_location": has_location,
        "has_linkedin_or_portfolio": has_linkedin_or_portfolio,
        "detected_headings": detected_headings,
        "non_standard_headings": non_standard_headings,
        "has_summary": has_summary,
        "has_experience": has_experience,
        "has_education": has_education,
        "has_skills": has_skills,
        "has_projects": has_projects,
        "has_certifications": has_certifications,
        "has_leadership": has_leadership,
        "uses_standard_headings": uses_standard_headings,
        "skills_categorized": skills_categorized,
        "skill_category_count": skill_category_count,
        "total_bullets": total_bullets,
        "quantified_bullets": quantified_bullets,
        "quantified_pct": quantified_pct,
        "has_gpa_or_coursework": has_gpa_or_coursework,
        "searchable_text": searchable_text,
    }


def format_cv_fact_sheet(facts: dict[str, object]) -> str:
    """Format extracted CV facts as an authoritative checklist for the grading LLM."""
    detected_headings: dict[str, str] = facts["detected_headings"]  # type: ignore[assignment]
    non_standard: list[str] = facts["non_standard_headings"]  # type: ignore[assignment]
    heading_list = ", ".join(f"'{v}'" for v in detected_headings.values()) or "None"
    quant_pct = int(facts.get("quantified_pct", 0))  # type: ignore[arg-type]

    lines = [
        "=== VERIFIED DOCUMENT FACT SHEET (GROUND TRUTH — DO NOT CONTRADICT) ===",
        f"- Email Address: {'[PRESENT / VERIFIED]' if facts['has_email'] else '[MISSING]'}",
        f"- Phone Number: {'[PRESENT / VERIFIED]' if facts['has_phone'] else '[MISSING]'}",
        f"- Location: {'[PRESENT / VERIFIED]' if facts['has_location'] else '[MISSING]'}",
        f"- LinkedIn / Portfolio / GitHub Link: {'[PRESENT / VERIFIED]' if facts['has_linkedin_or_portfolio'] else '[MISSING]'}",
        f"- Professional Summary Section: {'[PRESENT / VERIFIED]' if facts['has_summary'] else '[NOT PRESENT]'}",
        f"- Detected Standard ATS Headings: {heading_list}",
        (
            "- Standard ATS Headings Check: [PRESENT / VERIFIED — DO NOT suggest standardizing headings]"
            if facts["uses_standard_headings"]
            else f"- Non-Standard or Missing Core Headings Detected: {non_standard or 'Missing core section headings'}"
        ),
        (
            f"- Skills Format: [CATEGORIZED into {facts['skill_category_count']} categories — DO NOT suggest categorizing or grouping skills]"
            if facts["skills_categorized"]
            else "- Skills Format: [FLAT / UNCATEGORIZED OR MISSING]"
        ),
        (
            f"- Resume Length: [CONCISE / 1-2 PAGES ({facts['word_count']} words) — DO NOT suggest shortening or tightening length]"
            if facts["is_concise_length"]
            else f"- Resume Length: [LONG ({facts['word_count']} words)]"
        ),
        (
            f"- Work Experience Quantification: [STRONG / VERIFIED — {facts['quantified_bullets']}/{facts['total_bullets']} bullets ({quant_pct}%) contain measurable metrics (>=60% full-marks threshold met) — DO NOT suggest adding quantitative metrics to work experience bullets]"
            if quant_pct >= 60
            else f"- Work Experience Quantification: [{facts['quantified_bullets']}/{facts['total_bullets']} bullets ({quant_pct}%) contain measurable metrics]"
        ),
        f"- Education GPA / Coursework / Honors: {'[PRESENT / VERIFIED]' if facts['has_gpa_or_coursework'] else '[NOT LISTED]'}",
        "=======================================================================",
    ]
    return "\n".join(lines)


def _build_false_positive_patterns(
    facts: dict[str, object],
    include_exp_metrics: bool = True,
) -> list[re.Pattern[str]]:
    """Build regex patterns that match false-positive feedback contradicting verified facts."""
    patterns: list[re.Pattern[str]] = []

    _include_cue = r"(?:should\s+include|consider\s+including|by\s+including|try\s+including|recommend\s+including|^include)"

    if facts.get("has_summary"):
        patterns.append(
            re.compile(
                rf"\b(?:add(?:ing)?|{_include_cue}|writ(?:e|ing)|creat(?:e|ing)|insert(?:ing)?|"
                r"provid(?:e|ing)|lack(?:s|ing)?|missing|no|without|absent|omit(?:s|ted|ting)?)\b"
                r"[^.!?;]*\b(?:professional\s+summary|executive\s+summary|career\s+summary|"
                r"summary\s+section|summary\s+statement|brief\s+summary|resume\s+summary|objective)\b",
                re.IGNORECASE,
            )
        )
        patterns.append(
            re.compile(
                r"\b(?:professional\s+summary|executive\s+summary|summary\s+section|brief\s+summary)\b"
                r"[^.!?;]*\b(?:missing|absent|not\s+present|not\s+included|should\s+be\s+added|could\s+be\s+added)\b",
                re.IGNORECASE,
            )
        )

    if facts.get("uses_standard_headings"):
        patterns.append(
            re.compile(
                r"\b(?:standardiz(?:e|ing)|non-?standard|unconventional|renam(?:e|ing)|align(?:ing)?)\b"
                r"[^.!?;]*\b(?:section\s+)?(?:heading|header|title)s?\b",
                re.IGNORECASE,
            )
        )
        patterns.append(
            re.compile(
                r"\b(?:section\s+)?(?:heading|header|title)s?\b[^.!?;]*"
                r"\b(?:standardiz(?:e|ed|ing)|non-?standard|unconventional|standard\s+ats)\b",
                re.IGNORECASE,
            )
        )

    if facts.get("is_concise_length"):
        patterns.append(
            re.compile(
                r"\b(?:tighten(?:ing)?|shorten(?:ing)?|reduc(?:e|ing)|trim(?:ming)?|condens(?:e|ing)|cut(?:ting)?)\b"
                r"[^.!?;]*\b(?:resume\s+length|cv\s+length|overall\s+length|page\s+length|document\s+length|length|page\s+count|to\s+1[-–]2\s+pages)\b",
                re.IGNORECASE,
            )
        )

    if facts.get("skills_categorized"):
        patterns.append(
            re.compile(
                r"\b(?:categoriz(?:e|ing)|group(?:ing)?|organiz(?:e|ing)|split(?:ting)?|divid(?:e|ing)|structur(?:e|ing)|re-?format(?:ting)?)\b"
                r"[^.!?;]*\bskills?\b[^.!?;]*\b(?:categor(?:y|ies)|sub-?categories|groups?|buckets?|sections?)\b",
                re.IGNORECASE,
            )
        )
        patterns.append(
            re.compile(
                r"\b(?:flat\s+skills?(?:\s+list)?|uncategorized\s+skills?)\b",
                re.IGNORECASE,
            )
        )

    if include_exp_metrics and int(facts.get("quantified_pct", 0)) >= 60:  # type: ignore[arg-type]
        patterns.append(
            re.compile(
                rf"\b(?:add(?:ing)?|{_include_cue}|provid(?:e|ing)|incorporat(?:e|ing)|insert(?:ing)?|need(?:s)?|lack(?:s|ing)?)\b"
                r"[^.!?;]*\b(?:quantitativ(?:e|ely)|quantifi(?:ed|able)|measurable|numeric(?:al)?)\s+"
                r"(?:metrics?|measurements?|outcomes?|results?|impact|achievements?|data|figures?)\b"
                r"(?![^.!?;]*\b(?:project|leadership|volunteer|activit))",
                re.IGNORECASE,
            )
        )
        patterns.append(
            re.compile(
                r"\b(?:quantify(?:ing)?)\b[^.!?;]*\b(?:work\s+experience|experience\s+bullets?|professional\s+experience|bullets?|achievements?)\b"
                r"(?![^.!?;]*\b(?:project|leadership|volunteer|activit))",
                re.IGNORECASE,
            )
        )

    if facts.get("has_email") and facts.get("has_phone") and facts.get("has_linkedin_or_portfolio"):
        patterns.append(
            re.compile(
                rf"\b(?:add(?:ing)?|{_include_cue}|provid(?:e|ing)|missing|lack(?:s|ing)?)\b"
                r"[^.!?;]*\b(?:linkedin|portfolio|github|email|phone\s+number|contact\s+link|profile\s+link|url)s?\b",
                re.IGNORECASE,
            )
        )

    if facts.get("has_gpa_or_coursework"):
        patterns.append(
            re.compile(
                rf"\b(?:add(?:ing)?|{_include_cue}|list(?:ing)?|missing|lack(?:s|ing)?)\b"
                r"[^.!?;]*\b(?:gpa|relevant\s+coursework|coursework)\b",
                re.IGNORECASE,
            )
        )

    return patterns


def _is_false_positive_text(text: str, patterns: list[re.Pattern[str]]) -> bool:
    """Return True if text matches any verified false-positive pattern."""
    return any(p.search(text) for p in patterns)


def _clean_prose_false_positives(
    prose: str,
    patterns: list[re.Pattern[str]],
    fallback_text: str,
) -> str:
    """Strip sentences containing false-positive claims from a multi-sentence paragraph."""
    if not prose or not patterns:
        return prose
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", prose.strip()) if s.strip()]
    kept = [s for s in sentences if not _is_false_positive_text(s, patterns)]
    if not kept:
        return fallback_text
    return " ".join(kept)


def _append_unique_if_missing(items: list[str], candidate: str, keyword_check: str) -> None:
    """Append a deterministic gap suggestion if no existing item already covers that topic."""
    lower_check = keyword_check.lower()
    if not any(lower_check in item.lower() for item in items):
        items.append(candidate)


def _enforce_verifiable_gaps(
    result: ATSCheckResult,
    facts: dict[str, object],
) -> None:
    """Prevent false negatives by capping inflated scores and surfacing missed verifiable defects."""
    missing_contact_items: list[str] = []
    max_contact_score = 25  # Assume name present unless contact section absent
    if facts.get("has_email"):
        max_contact_score += 25
    else:
        missing_contact_items.append("email address")
    if facts.get("has_phone"):
        max_contact_score += 25
    else:
        missing_contact_items.append("phone number")
    if facts.get("has_location"):
        max_contact_score += 12
    else:
        missing_contact_items.append("city/country location")
    if facts.get("has_linkedin_or_portfolio"):
        max_contact_score += 13
    else:
        missing_contact_items.append("LinkedIn or portfolio link")

    non_standard: list[str] = facts.get("non_standard_headings") or []  # type: ignore[assignment]
    is_concise = bool(facts.get("is_concise_length", True))
    word_count = int(facts.get("word_count", 0))  # type: ignore[arg-type]
    has_skills = bool(facts.get("has_skills"))
    skills_categorized = bool(facts.get("skills_categorized"))
    total_bullets = int(facts.get("total_bullets", 0))  # type: ignore[arg-type]
    quantified_pct = int(facts.get("quantified_pct", 0))  # type: ignore[arg-type]

    if non_standard:
        heading_preview = ", ".join(f"'{h}'" for h in non_standard[:3])
        if not any("heading" in i.issue.lower() or "non-standard" in i.issue.lower() for i in result.formatting_issues):
            result.formatting_issues.append(
                ATSFormattingIssue(
                    issue=f"Non-standard section headings detected ({heading_preview})",
                    severity="Medium",
                    suggestion="Rename headings to standard ATS labels such as 'Professional Summary', 'Professional Experience', 'Education', and 'Technical Skills'.",
                )
            )
        _append_unique_if_missing(
            result.improvements,
            f"Replace non-standard headings ({heading_preview}) with standard ATS section titles.",
            "heading",
        )

    if not is_concise:
        if not any("length" in i.issue.lower() or "word" in i.issue.lower() or "page" in i.issue.lower() for i in result.formatting_issues):
            result.formatting_issues.append(
                ATSFormattingIssue(
                    issue=f"Resume length is {word_count} words, which may exceed 2 pages",
                    severity="Low",
                    suggestion="Tighten older or redundant bullets to keep the resume concise (1-2 pages).",
                )
            )
        _append_unique_if_missing(
            result.improvements,
            f"Trim resume content ({word_count} words) to keep the document concise at 1-2 pages.",
            "length",
        )

    for section in result.sections:
        key = _canonical_section_key(section.section_name)

        if key == "contact" and missing_contact_items:
            section.score = min(section.score, max_contact_score)
            for item in missing_contact_items:
                token = item.split()[0]
                _append_unique_if_missing(
                    section.suggestions,
                    f"Add a {item} to the contact header.",
                    token,
                )
                if token in ("email", "phone"):
                    _append_unique_if_missing(
                        result.improvements,
                        f"Add your {item} to the contact header for recruiter outreach and ATS parsing.",
                        token,
                    )

        elif key == "formatting":
            if non_standard:
                section.score = min(section.score, 75)
                _append_unique_if_missing(
                    section.suggestions,
                    f"Rename non-standard headings ({', '.join(non_standard[:3])}) to standard ATS section titles.",
                    "heading",
                )
            if not is_concise:
                section.score = min(section.score, 80)
                _append_unique_if_missing(
                    section.suggestions,
                    f"Condense resume length ({word_count} words) to fit cleanly within 1-2 pages.",
                    "length",
                )

        elif key == "skills" and has_skills and not skills_categorized:
            section.score = min(section.score, 85)
            _append_unique_if_missing(
                section.suggestions,
                "Group skills into up to 3 clear domain categories for faster ATS and recruiter scanning.",
                "categor",
            )

        elif key == "experience" and total_bullets >= 3 and quantified_pct < 40:
            cap = 70 if quantified_pct < 15 else 80
            section.score = min(section.score, cap)
            _append_unique_if_missing(
                section.suggestions,
                f"Quantify more experience bullets with measurable outcomes (currently {quantified_pct}% contain metrics).",
                "quantif",
            )
            _append_unique_if_missing(
                result.improvements,
                f"Add measurable metrics (%, volume, turnaround time, or financial/outcome impact) to experience bullets ({quantified_pct}% currently quantified).",
                "metric",
            )


def _prune_false_positive_feedback(
    result: ATSCheckResult,
    normalized_text: str,
    facts: dict[str, object],
) -> ATSCheckResult:
    """Deterministically reconcile feedback against verified CV facts (block false positives and false negatives)."""
    fp_patterns = _build_false_positive_patterns(facts, include_exp_metrics=True)
    non_exp_fp_patterns = _build_false_positive_patterns(facts, include_exp_metrics=False)
    lower_cv_text = normalized_text.lower()

    # 1. Deduplicate detected_keywords and verify missing_common_keywords are not actually present
    if result.keyword_analysis:
        deduped_detected: list[str] = []
        existing_detected_lower: set[str] = set()
        for kw in result.keyword_analysis.detected_keywords:
            kw_clean = kw.strip()
            if kw_clean and kw_clean.lower() not in existing_detected_lower:
                deduped_detected.append(kw_clean)
                existing_detected_lower.add(kw_clean.lower())
        result.keyword_analysis.detected_keywords = deduped_detected

        verified_missing: list[str] = []
        seen_missing_lower: set[str] = set()
        for kw in result.keyword_analysis.missing_common_keywords:
            kw_clean = kw.strip()
            if not kw_clean:
                continue
            kw_lower = kw_clean.lower()
            # Check if keyword already appears in the CV text
            kw_pattern = r"\b" + re.escape(kw_lower) + r"\b"
            if re.search(kw_pattern, lower_cv_text) or kw_lower in lower_cv_text:
                if kw_lower not in existing_detected_lower:
                    result.keyword_analysis.detected_keywords.append(kw_clean)
                    existing_detected_lower.add(kw_lower)
            elif kw_lower not in seen_missing_lower and kw_lower not in existing_detected_lower:
                verified_missing.append(kw_clean)
                seen_missing_lower.add(kw_lower)
        result.keyword_analysis.missing_common_keywords = verified_missing

    # 2. Filter formatting_issues against verified facts
    result.formatting_issues = [
        issue
        for issue in result.formatting_issues
        if not _is_false_positive_text(f"{issue.issue}. {issue.suggestion}", fp_patterns)
    ]

    # 3. Filter top-level improvements against verified facts
    result.improvements = [
        imp for imp in result.improvements if not _is_false_positive_text(imp, fp_patterns)
    ]

    # 4. Drop absent optional sections so they never drag down weighted score, then enforce ground truth
    filtered_sections: list[ATSSectionScore] = []
    has_exp = bool(facts.get("has_experience"))
    level = _normalize_level(result.candidate_level)
    for section in result.sections:
        key = _canonical_section_key(section.section_name)
        is_absent_in_facts = key in ("summary", "projects", "certifications", "leadership") and not facts.get(f"has_{key}")
        is_absent_section = (not section.present) or is_absent_in_facts
        if is_absent_section:
            if key in ("certifications", "leadership"):
                continue
            if key in ("summary", "projects") and (has_exp or level != "Entry-Level"):
                continue
        filtered_sections.append(section)
    result.sections = filtered_sections

    all_contact_present = bool(
        facts.get("has_email")
        and facts.get("has_phone")
        and facts.get("has_location")
        and facts.get("has_linkedin_or_portfolio")
    )
    clean_formatting = bool(
        facts.get("uses_standard_headings")
        and facts.get("is_concise_length")
        and len(result.formatting_issues) == 0
    )

    for section in result.sections:
        key = _canonical_section_key(section.section_name)

        if key == "contact" and all_contact_present:
            section.score = 100
            section.suggestions = []
            section.feedback = _clean_prose_false_positives(
                section.feedback,
                fp_patterns,
                "Complete contact details including full name, email, phone number, location, and professional profile links are clearly presented.",
            )
            continue

        if key == "formatting" and clean_formatting:
            section.score = 100
            section.suggestions = []
            section.feedback = _clean_prose_false_positives(
                section.feedback,
                fp_patterns,
                "Clean single-column layout with standard ATS section headings, consistent date formatting, and concise length.",
            )
            continue

        section_patterns = non_exp_fp_patterns if key in ("projects", "leadership") else fp_patterns
        orig_sug_count = len(section.suggestions)
        section.suggestions = [
            s for s in section.suggestions if not _is_false_positive_text(s, section_patterns)
        ]
        removed_fp_sug = len(section.suggestions) < orig_sug_count
        section.feedback = _clean_prose_false_positives(
            section.feedback,
            section_patterns,
            f"Strong {section.section_name} section aligned with ATS expectations.",
        )

        # Only recover docked points when the sole deduction was a stripped false-positive structural claim,
        # preserving contextual relevance scores and valid role-fit suggestions intact.
        if key == "skills" and facts.get("skills_categorized") and removed_fp_sug and not section.suggestions:
            section.score = max(section.score, 95)
        elif (
            key == "experience"
            and int(facts.get("quantified_pct", 0)) >= 60  # type: ignore[arg-type]
            and removed_fp_sug
            and not section.suggestions
        ):
            min_exp_score = 100 if int(facts.get("quantified_pct", 0)) >= 75 else 95  # type: ignore[arg-type]
            section.score = max(section.score, min_exp_score)

        if section.score == 100:
            section.suggestions = []

    # 5. Enforce verifiable real defects so false negatives cannot slip through
    _enforce_verifiable_gaps(result, facts)

    # 6. Clean executive summary of any sentence containing false-positive claims
    if result.summary:
        cleaned_summary = _clean_prose_false_positives(
            result.summary,
            fp_patterns,
            "The resume demonstrates strong ATS compatibility with well-structured sections, standard headings, and relevant domain keywords.",
        )
        summary_sentences = [
            s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned_summary) if s.strip()
        ]
        if len(summary_sentences) < 2:
            if result.improvements:
                top_imp = result.improvements[0].rstrip(".")
                first_char = top_imp[0].lower() + top_imp[1:] if len(top_imp) > 1 else top_imp.lower()
                summary_sentences.append(f"As a next step, {first_char}.")
            else:
                summary_sentences.append(
                    "All core ATS structural, formatting, and content standards are well satisfied."
                )
        result.summary = " ".join(summary_sentences)

    return result


def normalize_and_score_ats_result(
    result: ATSCheckResult,
    normalized_text: str | None = None,
    facts: dict[str, object] | None = None,
) -> ATSCheckResult:
    """Enforce ground-truth feedback filtering, canonical level weights, and deterministic overall_score."""
    level = _normalize_level(result.candidate_level)
    result.candidate_level = level
    level_weights = _CANONICAL_WEIGHTS[level]

    if normalized_text is not None:
        resolved_facts = facts if facts is not None else extract_cv_facts(normalized_text)
        result = _prune_false_positive_feedback(result, normalized_text, resolved_facts)

    if not result.sections:
        return result

    raw_weights: list[float] = []
    for section in result.sections:
        key = _canonical_section_key(section.section_name)
        base_weight = level_weights.get(key)
        if base_weight is not None:
            raw_weights.append(base_weight)
        else:
            raw_weights.append(max(section.weight, 0.05))

    total_weight = sum(raw_weights)
    if total_weight <= 0:
        equal_weight = round(1.0 / len(result.sections), 4)
        normalized_weights = [equal_weight] * len(result.sections)
    else:
        normalized_weights = [round(w / total_weight, 4) for w in raw_weights]

    # Adjust largest weight so weights sum cleanly to 1.0000
    diff = round(1.0 - sum(normalized_weights), 4)
    if diff != 0 and normalized_weights:
        max_idx = max(range(len(normalized_weights)), key=lambda i: normalized_weights[i])
        normalized_weights[max_idx] = round(normalized_weights[max_idx] + diff, 4)

    updated_sections: list[ATSSectionScore] = []
    weighted_sum = 0.0
    for section, weight in zip(result.sections, normalized_weights):
        clamped_score = max(0, min(100, int(round(section.score))))
        updated_sections.append(
            section.model_copy(update={"score": clamped_score, "weight": weight})
        )
        weighted_sum += clamped_score * weight

    result.sections = updated_sections
    result.overall_score = max(0, min(100, int(round(weighted_sum))))
    # Defensive guard: keep any explicit X/100 mention in summary aligned with overall_score
    if result.summary:
        result.summary = re.sub(
            r"\b\d{1,3}\s*/\s*100\b",
            f"{result.overall_score}/100",
            result.summary,
        )
    return result


def normalize_cv_text(raw_text: str) -> str:
    """Normalize extracted CV text so whitespace/hyphen/line-ending differences do not change hashes."""
    cleaned = raw_text.replace("\xa0", " ")
    cleaned = re.sub(r"[\u2010\u2011\u2012\u2013\u2212]", "-", cleaned)
    lines = [re.sub(r"\s+", " ", line).strip() for line in cleaned.splitlines()]
    return "\n".join(line for line in lines if line)


def _cache_get(cache: OrderedDict, key: str):
    """Retrieve a non-expired deep copy from an LRU TTL cache."""
    now = time.monotonic()
    with _CACHE_LOCK:
        entry = cache.get(key)
        if entry is None:
            return None
        expires_at, cached = entry
        if now < expires_at:
            cache.move_to_end(key)
            return cached.model_copy(deep=True)
        cache.pop(key, None)
        return None


def _cache_set(cache: OrderedDict, key: str, value) -> None:
    """Store a deep copy in an LRU TTL cache and evict expired/excess entries."""
    now = time.monotonic()
    with _CACHE_LOCK:
        expired_keys = [k for k, (exp, _) in cache.items() if now >= exp]
        for k in expired_keys:
            cache.pop(k, None)
        cache[key] = (now + _CACHE_TTL_SECONDS, value.model_copy(deep=True))
        cache.move_to_end(key)
        while len(cache) > _CACHE_MAX_SIZE:
            cache.popitem(last=False)


def parse_cv_to_structured(raw_text: str) -> ParsedCVDocument:
    """Parse normalized raw CV text into a canonical ParsedCVDocument (TailoredCV + PersonalInfo JSON)."""
    normalized = normalize_cv_text(raw_text)
    cache_key = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    cached = _cache_get(_PARSE_CACHE, cache_key)
    if cached is not None:
        return cached

    structured_llm = get_structured_llm(ParsedCVDocument, temperature=0)
    messages = [
        SystemMessage(content=CV_PARSER_SYSTEM_PROMPT),
        HumanMessage(content=f"CV/Resume Text:\n\n{normalized}"),
    ]

    parsed = structured_llm.invoke(messages)

    # Deterministic reconciliation against raw text so contact links/word count/skill categories are exact
    parsed.word_count = len(normalized.split())
    text_facts = extract_cv_facts(normalized)
    if text_facts.get("has_linkedin_or_portfolio") and not (
        (parsed.personal_info.linkedin_url and parsed.personal_info.linkedin_url.strip())
        or (parsed.personal_info.portfolio_url and parsed.personal_info.portfolio_url.strip())
        or (parsed.personal_info.other_url and parsed.personal_info.other_url.strip())
    ):
        parsed.personal_info.linkedin_url = "LinkedIn"

    active_skill_cats = [c for c in parsed.skills if c.items]
    if len(active_skill_cats) >= 2 or bool(text_facts.get("skills_categorized")):
        parsed.skills_are_categorized = True

    _cache_set(_PARSE_CACHE, cache_key, parsed)
    return parsed


def grade_parsed_cv(
    doc: ParsedCVDocument,
    target_role: str | None = None,
    company_name: str | None = None,
    job_description: str | None = None,
) -> ATSCheckResult:
    """Grade a structured ParsedCVDocument JSON using the unified ATS rubric and 24h TTL cache."""
    clean_role = target_role.strip()[:120] if target_role and target_role.strip() else None
    clean_company = company_name.strip()[:120] if company_name and company_name.strip() else None
    clean_jd = job_description.strip()[:2500] if job_description and job_description.strip() else None
    canonical_json = doc.model_dump_json()
    jd_hash = hashlib.sha256(clean_jd.encode("utf-8")).hexdigest() if clean_jd else ""
    cache_payload = (
        f"{canonical_json}|role={clean_role.lower() if clean_role else ''}"
        f"|company={clean_company.lower() if clean_company else ''}"
        f"|jd={jd_hash}"
    )
    cache_key = hashlib.sha256(cache_payload.encode("utf-8")).hexdigest()
    cached = _cache_get(_ATS_CACHE, cache_key)
    if cached is not None:
        return cached

    facts = extract_facts_from_parsed_cv(doc)
    fact_sheet = format_cv_fact_sheet(facts)
    role_line = (
        f"TARGET ROLE: {clean_role}"
        if clean_role
        else "TARGET ROLE: Inferred from CV (grade domain relevance & credential strength against primary role)"
    )
    context_lines = [role_line]
    if clean_company:
        context_lines.append(f"TARGET COMPANY: {clean_company}")
    if clean_jd:
        context_lines.append(
            f"TARGET JOB DESCRIPTION (prioritize keyword coverage and requirement alignment against this JD):\n{clean_jd}"
        )
    target_context = "\n".join(context_lines)

    structured_llm = get_structured_llm(ATSCheckResult, temperature=0)
    messages = [
        SystemMessage(content=ATS_SCORING_RUBRIC),
        HumanMessage(
            content=(
                f"{target_context}\n\n"
                f"{fact_sheet}\n\n"
                f"PARSED CV JSON:\n{doc.model_dump_json(exclude_none=True)}"
            )
        ),
    ]

    result = structured_llm.invoke(messages)
    searchable_text = str(facts.get("searchable_text") or "")
    scored = normalize_and_score_ats_result(
        result,
        normalized_text=normalize_cv_text(searchable_text),
        facts=facts,
    )
    scored.target_role = clean_role
    scored.company_name = clean_company

    _cache_set(_ATS_CACHE, cache_key, scored)
    return scored

