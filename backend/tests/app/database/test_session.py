"""Unit tests for app.database.session."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.database.session import check_db_connection, get_db


@pytest.mark.asyncio
async def test_get_db_commits_on_success_and_closes():
    session = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = False

    with patch("app.database.session.async_session_factory", return_value=cm):
        gen = get_db()
        yielded = await gen.__anext__()
        assert yielded is session
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()

    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_db_rolls_back_on_error_and_closes():
    session = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = False

    with patch("app.database.session.async_session_factory", return_value=cm):
        gen = get_db()
        await gen.__anext__()
        with pytest.raises(ValueError, match="boom"):
            await gen.athrow(ValueError("boom"))

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_db_connection_executes_select_1(mock_db):
    mock_db.execute = AsyncMock(return_value=MagicMock())
    await check_db_connection(mock_db)
    mock_db.execute.assert_awaited_once()
