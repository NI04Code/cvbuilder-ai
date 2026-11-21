"""Unit tests for app.models.profile."""

from datetime import timezone

from app.models.profile import Profile, utcnow


def test_profile_model():
    assert utcnow().tzinfo is timezone.utc
    assert Profile.__tablename__ == "profiles"
