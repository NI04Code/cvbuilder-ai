"""Unit tests for app.schemas.document."""

import pytest
from pydantic import ValidationError

from app.schemas.document import JobTargetedRequest


def test_job_targeted_request_sanitizes_and_validates_lengths():
    req = JobTargetedRequest(
        job_description="<script>alert(1)</script>" + "A" * 60 + "\x00",
        job_title="<b>Senior Engineer</b>",
        company_name="Acme\x00Corp",
    )
    assert "<script>" not in req.job_description
    assert "\x00" not in req.job_description
    assert req.job_title == "Senior Engineer"
    assert req.company_name == "AcmeCorp"

    with pytest.raises(ValidationError):
        JobTargetedRequest(job_description="too short")
