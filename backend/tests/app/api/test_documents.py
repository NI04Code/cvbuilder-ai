"""Unit tests for app.api.documents."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.database import get_db
from app.main import app
from app.schemas.document import DocumentHistoryItem
from app.security.jwt import get_current_user
from tests.conftest import make_user


@pytest.mark.asyncio
async def test_list_generated_documents_endpoint(mock_db):
    user = make_user()
    item = DocumentHistoryItem(
        id=uuid.uuid4(),
        document_type="cv",
        job_title="SWE",
        company_name="Acme",
        ats_score=90.0,
        created_at=datetime.now(timezone.utc),
    )

    async def _override_db():
        yield mock_db

    async def _override_user():
        return user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("app.api.documents.list_unified_documents", new=AsyncMock(return_value=[item])) as mock_list:
                resp = await client.get("/api/documents/history?document_type=cv&limit=15&offset=5")
            assert resp.status_code == 200
            assert resp.json()[0]["document_type"] == "cv"
            mock_list.assert_awaited_once_with(
                mock_db, user.id, document_type="cv", limit=15, offset=5
            )
    finally:
        app.dependency_overrides.clear()
