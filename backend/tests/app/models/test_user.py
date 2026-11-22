"""Unit tests for app.models.user."""

from datetime import timezone

from app.models.user import OAuthAccount, User, utcnow


def test_user_model_and_lazy_strategy():
    now = utcnow()
    assert now.tzinfo is timezone.utc
    assert User.__tablename__ == "users"
    assert OAuthAccount.__tablename__ == "oauth_accounts"
    for rel_name in (
        "oauth_accounts",
        "profile",
        "generated_cvs",
        "generated_cover_letters",
        "generated_cold_emails",
    ):
        assert User.__mapper__.relationships[rel_name].lazy == "raise"
