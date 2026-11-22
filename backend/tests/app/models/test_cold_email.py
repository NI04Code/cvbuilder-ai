"""Unit tests for app.models.cold_email."""

from datetime import timezone

from app.models.cold_email import GeneratedColdEmail, utcnow


def test_generated_cold_email_model():
    assert utcnow().tzinfo is timezone.utc
    assert GeneratedColdEmail.__tablename__ == "generated_cold_emails"
