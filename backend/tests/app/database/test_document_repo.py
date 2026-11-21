"""Unit tests for app.database.document_repo."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.database import document_repo
from app.models.generated_cv import GeneratedCV
from tests.conftest import make_generated_cv, make_scalar_result, make_scalars_result


@pytest.mark.asyncio
async def test_document_repo_crud(mock_db):
    uid = uuid.uuid4()
    cv = make_generated_cv(user_id=uid)

    mock_db.execute = AsyncMock(return_value=make_scalar_result(cv))
    assert await document_repo.get_owned_document(mock_db, GeneratedCV, cv.id, uid) is cv

    mock_db.execute = AsyncMock(return_value=make_scalars_result([cv]))
    items = await document_repo.list_by_user(mock_db, GeneratedCV, uid, limit=10, offset=0)
    assert items == [cv]

    saved = await document_repo.save_document(mock_db, cv)
    assert saved is cv
    mock_db.add.assert_called_once_with(cv)
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(cv)

    mock_db.reset_mock()
    await document_repo.delete_document(mock_db, cv)
    mock_db.delete.assert_awaited_once_with(cv)
    mock_db.commit.assert_awaited_once()
