"""Unit tests for app.security.encryption."""

import pytest
from cryptography.fernet import Fernet

from app.core import settings
from app.security.encryption import decrypt_secret, encrypt_secret


def test_encrypt_and_decrypt_with_configured_and_fallback_keys(monkeypatch):
    assert encrypt_secret(None) is None
    assert encrypt_secret("") is None
    assert decrypt_secret(None) is None
    assert decrypt_secret("legacy-plaintext") == "legacy-plaintext"

    # Configured Fernet key
    monkeypatch.setattr(settings, "oauth_token_encryption_key", Fernet.generate_key().decode("ascii"))
    enc = encrypt_secret("my-secret-token")
    assert enc is not None and enc.startswith("enc:")
    assert "my-secret-token" not in enc
    assert decrypt_secret(enc) == "my-secret-token"

    # Tampered payload raises ValueError
    with pytest.raises(ValueError, match="Failed to decrypt"):
        decrypt_secret("enc:invalid-token")

    # Derived non-production fallback when key is empty
    monkeypatch.setattr(settings, "oauth_token_encryption_key", "")
    enc2 = encrypt_secret("fallback-secret")
    assert enc2 is not None and decrypt_secret(enc2) == "fallback-secret"
