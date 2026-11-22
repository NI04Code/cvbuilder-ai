"""Unit tests for app.database.job_applications_repo."""

import uuid
from unittest.mock import MagicMock

import pytest

from app.database import job_applications_repo
from tests.conftest import make_job_application, make_scalar_result, make_scalars_result


@pytest.mark.asyncio
async def test_job_applications_repo_crud_and_filters(mock_db):
    user_id = uuid.uuid4()
    app_row = make_job_application(user_id=user_id)

    mock_db.execute.return_value = make_scalars_result([app_row])
    rows = await job_applications_repo.list_applications(mock_db, user_id, limit=20, offset=0)
    assert rows == [app_row]

    mock_db.execute.return_value = make_scalars_result([app_row])
    filtered = await job_applications_repo.list_applications(
        mock_db,
        user_id,
        status_filter="applied",
        search_query="Acme",
        limit=10,
        offset=5,
    )
    assert filtered == [app_row]

    count_result = MagicMock()
    count_result.all.return_value = [("applied", 3), ("interviewing", 1)]
    mock_db.execute.return_value = count_result
    counts = await job_applications_repo.count_by_status(mock_db, user_id)
    assert counts == {"applied": 3, "interviewing": 1}

    mock_db.execute.return_value = make_scalar_result(app_row)
    found = await job_applications_repo.get_owned_application(mock_db, app_row.id, user_id)
    assert found is app_row

    created = await job_applications_repo.create_application(mock_db, app_row)
    assert created is app_row
    mock_db.add.assert_called_once_with(app_row)
    mock_db.commit.assert_awaited()
    mock_db.refresh.assert_awaited_once_with(app_row)

    updated = await job_applications_repo.update_application(mock_db, app_row)
    assert updated is app_row

    await job_applications_repo.delete_application(mock_db, app_row)
    mock_db.delete.assert_awaited_once_with(app_row)
