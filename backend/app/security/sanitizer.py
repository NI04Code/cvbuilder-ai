"""Input sanitization utilities to prevent XSS and injection attacks."""

import os
import re
import uuid

import bleach


# Allowed HTML tags (none — we strip everything for plain-text inputs)
ALLOWED_TAGS: list[str] = []
ALLOWED_ATTRIBUTES: dict[str, list[str]] = {}


def sanitize_text(text: str) -> str:
    """Strip all HTML tags and dangerous characters from user input."""
    if not text:
        return text
    # Remove HTML tags
    cleaned = bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)
    # Remove null bytes
    cleaned = cleaned.replace("\x00", "")
    return cleaned.strip()


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal and other attacks.
    Returns a safe filename with a UUID prefix for uniqueness.
    """
    if not filename:
        return f"{uuid.uuid4().hex}.pdf"

    # Extract just the filename (prevent path traversal)
    filename = os.path.basename(filename)

    # Remove any non-alphanumeric characters except dots, hyphens, underscores
    safe_name = re.sub(r"[^\w.\-]", "_", filename)

    # Ensure it ends with .pdf
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"

    # Prefix with UUID to prevent collisions
    return f"{uuid.uuid4().hex}_{safe_name}"


def validate_file_type(content_type: str | None, filename: str | None) -> bool:
    """Validate that the uploaded file is a PDF."""
    allowed_types = {"application/pdf"}
    allowed_extensions = {".pdf"}

    type_ok = content_type in allowed_types if content_type else False
    ext_ok = (
        os.path.splitext(filename or "")[1].lower() in allowed_extensions
        if filename
        else False
    )

    return type_ok and ext_ok
