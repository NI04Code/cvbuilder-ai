"""Unit tests for app.security.rate_limiter."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.security.rate_limiter import limiter


def test_limiter_configuration():
    assert isinstance(limiter, Limiter)
    assert limiter._key_func is get_remote_address
