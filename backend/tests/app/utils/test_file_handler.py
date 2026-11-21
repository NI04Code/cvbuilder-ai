"""Unit tests for app.utils.file_handler."""

import io
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile

from app.utils.file_handler import (
    build_cv_filename,
    build_document_filename,
    delete_generated_document_file,
    get_generated_cv_path,
    get_generated_document_path,
    sanitize_filename_segment,
    save_upload_file,
)


@pytest.mark.asyncio
async def test_save_upload_file_validation_and_success(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("app.utils.file_handler.UPLOAD_DIR", tmp_path)
    uid = uuid.uuid4()

    bad_mime = UploadFile(
        filename="cv.txt",
        file=io.BytesIO(b"%PDF-1.4"),
        headers={"content-type": "text/plain"},
    )
    with pytest.raises(HTTPException) as exc1:
        await save_upload_file(bad_mime, uid)
    assert exc1.value.status_code == 400

    empty_file = UploadFile(
        filename="empty.pdf",
        file=io.BytesIO(b""),
        headers={"content-type": "application/pdf"},
    )
    with pytest.raises(HTTPException) as exc2:
        await save_upload_file(empty_file, uid)
    assert exc2.value.status_code == 400

    fake_pdf = UploadFile(
        filename="evil.pdf",
        file=io.BytesIO(b"not-a-pdf"),
        headers={"content-type": "application/pdf"},
    )
    with pytest.raises(HTTPException) as exc3:
        await save_upload_file(fake_pdf, uid)
    assert exc3.value.status_code == 400

    monkeypatch.setattr("app.utils.file_handler.MAX_FILE_SIZE", 10)
    oversize = UploadFile(
        filename="big.pdf",
        file=io.BytesIO(b"%PDF-" + b"x" * 20),
        headers={"content-type": "application/pdf"},
    )
    with pytest.raises(HTTPException) as exc4:
        await save_upload_file(oversize, uid)
    assert exc4.value.status_code == 413
    assert list((tmp_path / str(uid)).glob("*")) == []

    monkeypatch.setattr("app.utils.file_handler.MAX_FILE_SIZE", 1024 * 1024)
    valid = UploadFile(
        filename="../my resume.pdf",
        file=io.BytesIO(b"%PDF-1.4 valid"),
        headers={"content-type": "application/pdf"},
    )
    saved = await save_upload_file(valid, uid)
    assert saved.exists()
    assert saved.read_bytes() == b"%PDF-1.4 valid"


def test_filename_and_path_helpers_and_safe_delete(tmp_path: Path, monkeypatch):
    assert sanitize_filename_segment(" Acme / Corp! ", "Default") == "Acme-Corp"
    assert sanitize_filename_segment("   ", "Default") == "Default"

    assert build_document_filename("cv", "Acme Corp", "Alex", unique_code="ab12") == "cv-Acme-Corp-Alex-ab12.pdf"
    assert build_cv_filename(None, None) == "cv-Tailored-Candidate.pdf"

    monkeypatch.setattr("app.utils.file_handler.GENERATED_DIR", tmp_path)
    uid = uuid.uuid4()
    gen_path = get_generated_document_path(uid, "cv-Acme.pdf")
    assert gen_path.parent == tmp_path / str(uid)
    assert get_generated_cv_path(uid, "cv-Acme.pdf") == gen_path

    gen_path.write_bytes(b"%PDF-1.4")
    delete_generated_document_file(str(gen_path), uid)
    assert not gen_path.exists()

    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"%PDF-1.4")
    with pytest.raises(ValueError, match="outside"):
        delete_generated_document_file(str(outside), uid)
