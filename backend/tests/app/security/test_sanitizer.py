"""Unit tests for app.security.sanitizer."""

from app.security.sanitizer import (
    is_pdf_magic_bytes,
    sanitize_filename,
    sanitize_text,
    validate_file_type,
)


def test_sanitize_text():
    assert sanitize_text("") == ""
    assert sanitize_text("  <script>alert(1)</script>Hello\x00 World  ") == "alert(1)Hello World"
    assert sanitize_text("<b>Bold</b>") == "Bold"


def test_sanitize_filename():
    empty_name = sanitize_filename("")
    assert empty_name.endswith(".pdf")

    traversed = sanitize_filename("../../etc/passwd")
    assert "/" not in traversed and "\\" not in traversed
    assert traversed.endswith("_passwd.pdf")


def test_pdf_magic_bytes_and_validate_file_type():
    assert is_pdf_magic_bytes(b"%PDF-1.7\n...")
    assert not is_pdf_magic_bytes(b"<html>bad</html>")

    assert validate_file_type("application/pdf", "cv.pdf", b"%PDF-1.4")
    assert not validate_file_type("text/plain", "cv.pdf", b"%PDF-1.4")
    assert not validate_file_type("application/pdf", "cv.txt", b"%PDF-1.4")
    assert not validate_file_type("application/pdf", "cv.pdf", b"MZ\x90\x00")
