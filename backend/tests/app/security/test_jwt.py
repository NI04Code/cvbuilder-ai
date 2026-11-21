"""Unit tests for app.security.jwt."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.security.jwt import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    get_current_user,
)
from tests.conftest import make_user


def test_token_creation_and_decoding():
    uid = str(uuid.uuid4())
    acc = create_access_token(uid, "u@example.com")
    ref = create_refresh_token(uid)
    pair = create_token_pair(uid, "u@example.com")

    assert decode_token(acc)["type"] == "access"
    assert decode_token(ref)["type"] == "refresh"
    assert "jti" in decode_token(ref)
    assert pair["token_type"] == "bearer"

    with pytest.raises(HTTPException) as exc:
        decode_token("not.a.jwt")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_validation(mock_db):
    with pytest.raises(HTTPException) as no_creds:
        await get_current_user(credentials=None, db=mock_db)
    assert no_creds.value.status_code == 401

    user = make_user()
    pair = create_token_pair(str(user.id), user.email)

    # Refresh token rejected
    with pytest.raises(HTTPException) as bad_type:
        await get_current_user(credentials=MagicMock(credentials=pair["refresh_token"]), db=mock_db)
    assert bad_type.value.status_code == 401

    # Missing sub / invalid UUID
    with patch("app.security.jwt.decode_token", return_value={"type": "access"}):
        with pytest.raises(HTTPException):
            await get_current_user(credentials=MagicMock(credentials="x"), db=mock_db)

    with patch("app.security.jwt.decode_token", return_value={"type": "access", "sub": "bad-uuid"}):
        with pytest.raises(HTTPException):
            await get_current_user(credentials=MagicMock(credentials="x"), db=mock_db)

    # Inactive user rejected
    inactive = make_user(is_active=False)
    with patch("app.security.jwt.user_repo.get_user_by_id", new=AsyncMock(return_value=inactive)):
        with pytest.raises(HTTPException):
            await get_current_user(credentials=MagicMock(credentials=pair["access_token"]), db=mock_db)

    # Valid active user returned
    with patch("app.security.jwt.user_repo.get_user_by_id", new=AsyncMock(return_value=user)):
        resolved = await get_current_user(
            credentials=MagicMock(credentials=pair["access_token"]), db=mock_db
        )
    assert resolved is user
