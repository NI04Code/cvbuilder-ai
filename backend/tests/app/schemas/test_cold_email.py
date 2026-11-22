"""Unit tests for app.schemas.cold_email."""

import pytest
from pydantic import ValidationError

from app.schemas.cold_email import ColdEmailContent, ColdEmailGenerateRequest


def test_cold_email_generate_request_sanitizes_recruiter_name():
    req = ColdEmailGenerateRequest(
        job_description="A" * 60,
        job_title="Backend Engineer",
        company_name="Acme Corp",
        recruiter_name="  <b>Sarah Jenkins</b>\x00  ",
    )
    assert req.recruiter_name == "Sarah Jenkins"

    empty_recruiter = ColdEmailGenerateRequest(
        job_description="A" * 60,
        recruiter_name="   ",
    )
    assert empty_recruiter.recruiter_name is None

    with pytest.raises(ValidationError):
        ColdEmailGenerateRequest(job_description="short")


def test_cold_email_content_validation():
    content = ColdEmailContent(
        subject="Cut API latency 35% — Backend Engineer",
        email_body="Hi Sarah,\n\n" + "Concise hook and relevant impact. " * 4,
    )
    assert content.subject.startswith("Cut API latency")

    with pytest.raises(ValidationError):
        ColdEmailContent(subject="Hi", email_body="Too short")
