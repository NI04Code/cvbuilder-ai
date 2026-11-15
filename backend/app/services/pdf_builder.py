from datetime import datetime
from functools import lru_cache
from pathlib import Path
import re
import pymupdf
from jinja2 import Environment, FileSystemLoader
from app.schemas.cv import TailoredCV
from app.schemas.profile import PersonalInfo
from app.utils.url import infer_link_label, sanitize_external_url, strip_url_scheme

# Define template directory and optional font directories for Calibri
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_FONT_DIRS = [
    TEMPLATE_DIR / "fonts",
    Path("C:/Windows/Fonts"),
]
_CALIBRI_FILES = ("calibri.ttf", "calibrib.ttf", "calibrii.ttf", "calibriz.ttf")
_CALIBRI_FONT_FACE_CSS = """
@font-face { font-family: 'Calibri'; src: url(calibri.ttf); font-weight: normal; font-style: normal; }
@font-face { font-family: 'Calibri'; src: url(calibrib.ttf); font-weight: bold; font-style: normal; }
@font-face { font-family: 'Calibri'; src: url(calibrii.ttf); font-weight: normal; font-style: italic; }
@font-face { font-family: 'Calibri'; src: url(calibriz.ttf); font-weight: bold; font-style: italic; }
"""


@lru_cache(maxsize=1)
def _load_calibri_font_buffers() -> dict[str, bytes]:
    """
    Load Calibri TTF files into memory with the OpenType GSUB ligature table disabled
    so PDF text extraction for ATS parsers remains 100% pure ASCII ('ti', 'ft', 'tf', 'tt').
    """
    for font_dir in _FONT_DIRS:
        if all((font_dir / fname).exists() for fname in _CALIBRI_FILES):
            return {
                fname: (font_dir / fname).read_bytes().replace(b"GSUB", b"GSU_", 1)
                for fname in _CALIBRI_FILES
            }
    return {}


def _build_font_archive() -> tuple[pymupdf.Archive | None, str | None]:
    """Return a PyMuPDF Archive and @font-face CSS if Calibri font files are available."""
    buffers = _load_calibri_font_buffers()
    if not buffers:
        return None, None
    archive = pymupdf.Archive()
    for fname, data in buffers.items():
        archive.add(data, fname)
    return archive, _CALIBRI_FONT_FACE_CSS


_HEADER_MAX_CHARS = 85
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}(?:-\d{2})?$")


def _format_display_date(value: str | None) -> str | None:
    """Format YYYY-MM or YYYY-MM-DD dates as concise ATS 'Mon YYYY'; pass through all other strings."""
    if not value:
        return value
    cleaned = value.strip()
    if not _ISO_DATE_RE.match(cleaned):
        return cleaned
    fmt = "%Y-%m-%d" if len(cleaned) == 10 else "%Y-%m"
    try:
        return datetime.strptime(cleaned, fmt).strftime("%b %Y")
    except ValueError:
        return cleaned


def _build_header_items(personal_info: PersonalInfo) -> list[dict[str, str | None]]:
    """Build contact header items, shortening link labels when total header length exceeds one line."""
    candidates: list[dict[str, str | None]] = []
    for text_val in (personal_info.email, personal_info.phone, personal_info.location):
        if text_val and text_val.strip():
            clean_text = text_val.strip()
            candidates.append({"full": clean_text, "short": clean_text, "href": None})

    link_specs = (
        (personal_info.linkedin_url, "LinkedIn"),
        (personal_info.portfolio_url, "Portfolio"),
        (personal_info.other_url, "Other Link"),
    )
    for raw_url, fallback_label in link_specs:
        if not raw_url or not raw_url.strip():
            continue
        href = sanitize_external_url(raw_url)
        full_label = strip_url_scheme(href) if href else raw_url.strip()
        short_label = (
            infer_link_label(href, fallback_label)
            if href and fallback_label == "Other Link"
            else fallback_label
        )
        candidates.append({"full": full_label, "short": short_label, "href": href})

    if not candidates:
        return []

    full_line_len = len(" | ".join(str(item["full"]) for item in candidates))
    use_short = full_line_len > _HEADER_MAX_CHARS
    return [
        {
            "label": str(item["short"] if use_short else item["full"]),
            "href": item["href"],
        }
        for item in candidates
    ]


def _prepare_cv_context(cv: TailoredCV) -> dict:
    """Prepare CV dict with formatted display dates and validated safe URLs for rendering."""
    data = cv.model_dump()
    for exp in data.get("work_experiences", []):
        exp["start_date"] = _format_display_date(exp.get("start_date"))
        exp["end_date"] = _format_display_date(exp.get("end_date"))
    for edu in data.get("education", []):
        edu["start_date"] = _format_display_date(edu.get("start_date"))
        edu["end_date"] = _format_display_date(edu.get("end_date"))
    for act in data.get("leadership_activities", []):
        act["start_date"] = _format_display_date(act.get("start_date"))
        act["end_date"] = _format_display_date(act.get("end_date"))
    for cert in data.get("certifications", []):
        cert["date"] = _format_display_date(cert.get("date"))
        cert["safe_url"] = sanitize_external_url(cert.get("url"))
    for proj in data.get("projects", []):
        proj["safe_url"] = sanitize_external_url(proj.get("url"))
    return data


def generate_cv_pdf(cv: TailoredCV, personal_info: PersonalInfo, output_path: str) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    template = env.get_template("cv_template.html")

    # Render HTML with CV data
    html_out = template.render(
        cv=_prepare_cv_context(cv),
        personal_info=personal_info.model_dump(),
        header_items=_build_header_items(personal_info),
    )

    # Convert HTML to PDF with clickable hyperlink annotations using PyMuPDF Story
    # (A4 page with 0.8 inch / 57.6pt margins).
    archive, user_css = _build_font_archive()
    story = pymupdf.Story(html=html_out, user_css=user_css, archive=archive)
    mediabox = pymupdf.paper_rect("a4")
    margin = 57.6  # 0.8 in * 72 pt/in
    content_rect = mediabox + (margin, margin, -margin, -margin)

    def rectfn(rect_num: int, filled: pymupdf.Rect) -> tuple[pymupdf.Rect, pymupdf.Rect, None]:
        return mediabox, content_rect, None

    pdf_doc = story.write_with_links(rectfn)
    try:
        pdf_doc.save(output_path)
    finally:
        pdf_doc.close()

    return output_path
