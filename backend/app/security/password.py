"""Password hashing and constant-time verification using bcrypt via pwdlib."""

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.bcrypt import BcryptHasher

_password_hash = PasswordHash((BcryptHasher(),))


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return _password_hash.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Verify a plain-text password against a stored bcrypt hash safely."""
    if not hashed_password:
        return False
    try:
        return _password_hash.verify(plain_password, hashed_password)
    except (UnknownHashError, ValueError):
        return False
