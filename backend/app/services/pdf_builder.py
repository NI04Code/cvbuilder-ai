import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.schemas.cv import TailoredCV
from app.schemas.profile import PersonalInfo

# Define template directory
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

def generate_cv_pdf(cv: TailoredCV, personal_info: PersonalInfo, output_path: str) -> str:
    """
    Renders the ATS-friendly CV HTML template using Jinja2 and converts it to PDF using WeasyPrint.
    """
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("cv_template.html")
    
    # Render HTML with CV data
    html_out = template.render(
        cv=cv.model_dump(),
        personal_info=personal_info.model_dump()
    )
    
    # Convert to PDF
    HTML(string=html_out).write_pdf(output_path)
    
    return output_path
