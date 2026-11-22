"""Unit tests for app.schemas.job_applications."""

from datetime import date, datetime, timezone
import uuid

import pytest
from pydantic import ValidationError

from app.schemas.job_applications import (
    ApplicationCreateRequest,
    ApplicationResponse,
    ApplicationStatsResponse,
    ApplicationUpdateRequest,
)


def test_job_applications_create_validation_and_sanitization():
    req = ApplicationCreateRequest(
        company_name="<b>Stripe</b>",
        role_title="Backend Engineer<script>x</script>",
        job_url="stripe.com/jobs/123",
        status="applied",
        applied_date=date(2026, 11, 20),
        work_mode="hybrid",
        location="  Singapore  ",
        salary_range="$150k - $180k",
        recruiter_name="  Alex Lee ",
        recruiter_contact="alex@stripe.com",
        next_follow_up_date=date(2026, 11, 27),
        notes="Referral via <em>team</em>.",
    )
    assert req.company_name == "Stripe"
    assert req.role_title == "Backend Engineerx"
    assert req.job_url == "https://stripe.com/jobs/123"
    assert req.location == "Singapore"
    assert req.recruiter_name == "Alex Lee"
    assert req.notes == "Referral via team."

    minimal = ApplicationCreateRequest(
        company_name="Acme",
        role_title="SWE",
        job_url="   ",
        location="",
    )
    assert minimal.status == "saved"
    assert minimal.job_url is None
    assert minimal.location is None

    with pytest.raises(ValidationError):
        ApplicationCreateRequest(
            company_name="Acme",
            role_title="SWE",
            job_url="javascript:alert(1)",
        )

    with pytest.raises(ValidationError):
        ApplicationCreateRequest(
            company_name="Acme",
            role_title="SWE",
            status="ghosted",  # type: ignore[arg-type]
        )


def test_job_applications_update_validation_and_response():
    upd = ApplicationUpdateRequest(
        status="interviewing",
        job_url="",
        notes=None,
    )
    dumped = upd.model_dump(exclude_unset=True)
    assert dumped == {"status": "interviewing", "job_url": None, "notes": None}

    with pytest.raises(ValidationError):
        ApplicationUpdateRequest(company_name=None)  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        ApplicationUpdateRequest(status=None)  # type: ignore[arg-type]

    now = datetime.now(timezone.utc)
    resp = ApplicationResponse(
        id=uuid.uuid4(),
        company_name="Stripe",
        role_title="Backend Engineer",
        status="saved",
        created_at=now,
        updated_at=now,
    )
    assert resp.company_name == "Stripe"

    stats = ApplicationStatsResponse(total=2, saved=1, applied=1)
    assert stats.total == 2
    assert stats.interviewing == 0
