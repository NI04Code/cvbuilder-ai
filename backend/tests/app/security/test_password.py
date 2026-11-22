"""Unit tests for app.security.password."""

from app.security.password import hash_password, verify_password


def test_hash_and_verify_password():
    hashed = hash_password("StrongPass1")
    assert hashed != "StrongPass1"
    assert verify_password("StrongPass1", hashed) is True
    assert verify_password("WrongPass1", hashed) is False
    assert verify_password("StrongPass1", None) is False
    assert verify_password("StrongPass1", "not-a-valid-hash") is False
