"""Unit tests for app.core.settings."""

import pytest
from cryptography.fernet import Fernet

from app.core.settings import Settings


def test_parse_fallback_models_variants():
    assert Settings.parse_fallback_models('["m1", "m2"]') == ["m1", "m2"]
    assert Settings.parse_fallback_models("m1, m2 , ") == ["m1", "m2"]
    assert Settings.parse_fallback_models(["m1"]) == ["m1"]


def test_storage_properties_and_paths(tmp_path):
    s = Settings(
        upload_dir=str(tmp_path / "up"),
        generated_dir=str(tmp_path / "gen"),
        max_upload_size_mb=5,
    )
    assert s.max_upload_size_bytes == 5 * 1024 * 1024
    assert s.upload_path.is_dir()
    assert s.generated_path.is_dir()


def test_validate_production_secrets():
    # Non-production skips strict check
    Settings(environment="development", jwt_secret_key="CHANGE-ME-IN-PRODUCTION").validate_production_secrets()

    fernet_key = Fernet.generate_key().decode("ascii")
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        Settings(
            environment="production",
            jwt_secret_key="CHANGE-ME-IN-PRODUCTION",
            internal_auth_secret="s" * 16,
            oauth_token_encryption_key=fernet_key,
        ).validate_production_secrets()

    with pytest.raises(RuntimeError, match="INTERNAL_AUTH_SECRET"):
        Settings(
            environment="production",
            jwt_secret_key="j" * 32,
            internal_auth_secret="",
            oauth_token_encryption_key=fernet_key,
        ).validate_production_secrets()

    with pytest.raises(RuntimeError, match="OAUTH_TOKEN_ENCRYPTION_KEY"):
        Settings(
            environment="production",
            jwt_secret_key="j" * 32,
            internal_auth_secret="s" * 16,
            oauth_token_encryption_key="",
        ).validate_production_secrets()

    Settings(
        environment="production",
        jwt_secret_key="j" * 32,
        internal_auth_secret="s" * 16,
        oauth_token_encryption_key=fernet_key,
    ).validate_production_secrets()
