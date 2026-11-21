import os
import re
import uuid
from pathlib import Path

import aiofiles
from fastapi import HTTPException, UploadFile, status

from app.security.sanitizer import is_pdf_magic_bytes

# Define secure directories relative to project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
GENERATED_DIR = BASE_DIR / "generated"

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


async def save_upload_file(upload_file: UploadFile, user_id: str | uuid.UUID) -> Path:
    """
    Validates and saves an uploaded PDF file securely.
    Returns the absolute path to the saved file.
    """
    if upload_file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF files are allowed.",
        )

    # Validate PDF magic bytes before creating any file on disk
    header = await upload_file.read(5)
    await upload_file.seek(0)
    if not header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    if not is_pdf_magic_bytes(header):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file content. Only valid PDF files are allowed.",
        )

    # Sanitize filename to prevent path traversal
    safe_filename = f"{uuid.uuid4()}_{os.path.basename(upload_file.filename or 'resume.pdf')}"
    # Remove any potentially dangerous characters
    safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in "._- ")
    
    file_path = UPLOAD_DIR / str(user_id) / safe_filename
    
    # Ensure user directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Check file size by reading chunks asynchronously
    size = 0

    try:
        async with aiofiles.open(file_path, "wb") as buffer:
            while chunk := await upload_file.read(8192):
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024 * 1024)}MB.",
                    )
                await buffer.write(chunk)
    except Exception:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise

    # Reset file pointer if someone else needs to read it later
    await upload_file.seek(0)

    return file_path


def sanitize_filename_segment(value: str | None, default: str) -> str:
    """Normalizes a text segment into a safe hyphen-delimited filename token."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip()).strip("-")
    return cleaned or default


def build_document_filename(
    prefix: str,
    company: str | None,
    user_name: str | None,
    unique_code: str | None = None,
) -> str:
    """
    Builds a standardized generated document PDF filename:
    <prefix>-<company>-<user-name>[-<uniquecode>].pdf
    (e.g. prefix="cv", "cover-letter", or future document types).
    """
    prefix_part = sanitize_filename_segment(prefix, "document").lower()
    company_part = sanitize_filename_segment(company, "Tailored")
    name_part = sanitize_filename_segment(user_name, "Candidate")
    parts = [prefix_part, company_part, name_part]
    if unique_code:
        code_part = sanitize_filename_segment(unique_code, uuid.uuid4().hex[:8])
        parts.append(code_part)
    return f"{'-'.join(parts)}.pdf"


def build_cv_filename(
    company: str | None,
    user_name: str | None,
    unique_code: str | None = None,
) -> str:
    """Builds a standardized CV PDF filename: cv-<company>-<user-name>[-<uniquecode>].pdf."""
    return build_document_filename("cv", company, user_name, unique_code=unique_code)


def get_generated_document_path(user_id: str | uuid.UUID, filename: str) -> Path:
    """Returns a safe storage path inside the user's generated documents directory."""
    safe_filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
    user_dir = GENERATED_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / safe_filename


def get_generated_cv_path(user_id: str | uuid.UUID, filename: str) -> Path:
    """Alias for get_generated_document_path preserved for existing CV callers."""
    return get_generated_document_path(user_id, filename)


def delete_generated_document_file(file_path: str | None, user_id: str | uuid.UUID) -> None:
    """Safely delete a generated PDF only if it resides inside the user's generated directory."""
    if not file_path:
        return
    user_dir = (GENERATED_DIR / str(user_id)).resolve()
    target = Path(file_path).resolve()
    if not target.is_relative_to(user_dir):
        raise ValueError("Refusing to delete file outside user's generated directory.")
    if target.is_file():
        target.unlink()


def delete_generated_cv_file(file_path: str | None, user_id: str | uuid.UUID) -> None:
    """Alias for delete_generated_document_file preserved for existing CV callers."""
    delete_generated_document_file(file_path, user_id)
