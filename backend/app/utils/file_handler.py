import os
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

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

    # Sanitize filename to prevent path traversal
    safe_filename = f"{uuid.uuid4()}_{os.path.basename(upload_file.filename or 'resume.pdf')}"
    # Remove any potentially dangerous characters
    safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in "._- ")
    
    file_path = UPLOAD_DIR / str(user_id) / safe_filename
    
    # Ensure user directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Check file size by reading chunks
    size = 0
    
    with open(file_path, "wb") as buffer:
        while chunk := await upload_file.read(8192):
            size += len(chunk)
            if size > MAX_FILE_SIZE:
                # Clean up if too large
                os.remove(file_path)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024 * 1024)}MB.",
                )
            buffer.write(chunk)
            
    # Reset file pointer if someone else needs to read it later
    await upload_file.seek(0)
    
    return file_path


def get_generated_cv_path(user_id: str | uuid.UUID, filename: str) -> Path:
    """Returns a safe path for a generated CV."""
    safe_filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
    user_dir = GENERATED_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / safe_filename
