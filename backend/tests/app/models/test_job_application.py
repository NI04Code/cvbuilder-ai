"""Unit tests for app.models.job_application."""

from datetime import timezone

from app.models.job_application import JobApplication, utcnow


def test_job_application_model():
    assert utcnow().tzinfo is timezone.utc
    assert JobApplication.__tablename__ == "job_applications"
