"""Symmetric encryption helpers for sensitive tokens stored at rest."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core import settings

_ENC_PREFIX = "enc:"


def _get_fernet() -> Fernet:
    """Return a Fernet instance from OAUTH_TOKEN_ENCRYPTION_KEY (or derived dev key)."""
    configured = settings.oauth_token_encryption_key.strip()
    if configured:
        return Fernet(configured.encode("utf-8"))

    # Non-production fallback derived from jwt_secret_key so local dev works without extra setup
    digest = hashlib.sha256(settings.jwt_secret_key.encode("utf-8")).digest()
    derived_key = base64.urlsafe_b64encode(digest)
    return Fernet(derived_key)


def encrypt_secret(plaintext: str | None) -> str | None:
    """Encrypt a sensitive string for storage at rest; returns None for empty/None input."""
    if not plaintext:
        return None
    token = _get_fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")
    return f"{_ENC_PREFIX}{token}"


def decrypt_secret(ciphertext: str | None) -> str | None:
    """Decrypt a stored secret; raises ValueError if an encrypted payload fails verification."""
    if not ciphertext:
        return None
    if not ciphertext.startswith(_ENC_PREFIX):
        return ciphertext
    raw = ciphertext[len(_ENC_PREFIX) :].encode("ascii")
    try:
        return _get_fernet().decrypt(raw).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt stored secret") from exc
