from pathlib import Path
import pymupdf
from jinja2 import Environment, FileSystemLoader
from app.schemas.cv import TailoredCV
from app.schemas.profile import PersonalInfo

# Define template directory
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def generate_cv_pdf(cv: TailoredCV, personal_info: PersonalInfo, output_path: str) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("cv_template.html")

    # Render HTML with CV data
    html_out = template.render(
        cv=cv.model_dump(),
        personal_info=personal_info.model_dump(),
    )

    # Convert HTML to PDF using PyMuPDF Story (A4 page with 0.8 inch / 57.6pt margins)
    story = pymupdf.Story(html=html_out)
    mediabox = pymupdf.paper_rect("a4")
    margin = 57.6  # 0.8 in * 72 pt/in
    content_rect = mediabox + (margin, margin, -margin, -margin)

    writer = pymupdf.DocumentWriter(output_path)
    try:
        more = 1
        while more:
            device = writer.begin_page(mediabox)
            more, _ = story.place(content_rect)
            story.draw(device)
            writer.end_page()
    finally:
        writer.close()

    return output_path
