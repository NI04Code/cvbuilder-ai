"""Unit tests for app.models.generated_cv."""

from datetime import timezone

from app.models.generated_cv import GeneratedCV, utcnow


def test_generated_cv_model():
    assert utcnow().tzinfo is timezone.utc
    assert GeneratedCV.__tablename__ == "generated_cvs"
