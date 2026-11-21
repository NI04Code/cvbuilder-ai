"""Unit tests for app.models.cover_letter."""

from datetime import timezone

from app.models.cover_letter import GeneratedCoverLetter, utcnow


def test_generated_cover_letter_model():
    assert utcnow().tzinfo is timezone.utc
    assert GeneratedCoverLetter.__tablename__ == "generated_cover_letters"
