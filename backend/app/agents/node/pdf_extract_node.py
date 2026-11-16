"""Shared PDF text and hyperlink extraction nodes powered by PyMuPDF."""

import logging
from typing import TypedDict

import pymupdf as fitz

logger = logging.getLogger(__name__)


class FilePathExtractState(TypedDict, total=False):
    file_path: str
    raw_text: str
    error: str | None


class BytesExtractState(TypedDict, total=False):
    file_bytes: bytes
    raw_text: str
    error: str | None


def _extract_from_doc(doc: fitz.Document, *, sort_order: bool, include_links: bool) -> str:
    """Extract page text (optionally in reading order with embedded HTTP(S) URIs appended)."""
    text = ""
    link_uris: list[str] = []

    for page in doc:
        page_text = page.get_text("text", sort=sort_order) if sort_order else page.get_text()
        if page_text:
            text += (page_text.rstrip() + "\n") if sort_order else page_text
        if include_links:
            for link in page.get_links():
                uri = link.get("uri")
                if isinstance(uri, str) and uri.strip():
                    link_uris.append(uri.strip())

    if include_links and text.strip():
        lower_text = text.lower()
        embedded_uris: list[str] = []
        seen_uris: set[str] = set()
        for uri in link_uris:
            lower_uri = uri.lower()
            if not lower_uri.startswith(("http://", "https://")) or lower_uri in seen_uris:
                continue
            seen_uris.add(lower_uri)
            if lower_uri not in lower_text:
                embedded_uris.append(uri)
        if embedded_uris:
            text = f"{text.rstrip()}\nEmbedded Links: {' | '.join(embedded_uris)}"

    return text


def extract_resume_pdf_text_node(state: FilePathExtractState) -> dict:
    """Extract raw text from an uploaded resume PDF file path."""
    logger.info(f"Extracting text from {state['file_path']}")
    try:
        with fitz.open(state["file_path"]) as doc:
            text = _extract_from_doc(doc, sort_order=False, include_links=False)

        if not text.strip():
            return {**state, "error": "Could not extract text from PDF."}

        return {**state, "raw_text": text}
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        return {**state, "error": f"Failed to extract text: {str(e)}"}


def extract_ats_pdf_text_node(state: BytesExtractState) -> dict:
    """Extract reading-order text and embedded links from in-memory PDF bytes (no disk I/O)."""
    logger.info("ATS Checker: extracting text from uploaded PDF bytes")
    try:
        with fitz.open(stream=state["file_bytes"], filetype="pdf") as doc:
            text = _extract_from_doc(doc, sort_order=True, include_links=True)

        if not text.strip():
            return {
                **state,
                "error": "Could not extract any text from the PDF. The file may be image-based or corrupted.",
            }

        return {**state, "raw_text": text}
    except Exception as e:
        logger.error(f"ATS Checker: text extraction failed — {e}")
        return {**state, "error": f"Failed to read PDF: {str(e)}"}

