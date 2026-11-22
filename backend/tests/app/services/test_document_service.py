"""Unit tests for app.services.document_service."""

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.cold_email import GeneratedColdEmail
from app.models.generated_cv import GeneratedCV
from app.services import document_service
from tests.conftest import (
    make_generated_cold_email,
    make_generated_cover_letter,
    make_generated_cv,
    make_profile,
    make_profile_response,
    make_user,
)


@pytest.mark.asyncio
async def test_get_user_profile_for_generation_and_identity(mock_db):
    user = make_user(name="Fallback User")
    profile = make_profile(user_id=user.id)

    with patch("app.services.document_service.profile_repo.get_by_user_id", new=AsyncMock(return_value=profile)):
        prof, resp = await document_service.get_user_profile_for_generation(mock_db, user.id)
    assert prof is profile
    assert resp.user_id == user.id

    with patch("app.services.document_service.profile_repo.get_by_user_id", new=AsyncMock(return_value=None)):
        with pytest.raises(BadRequestError):
            await document_service.get_user_profile_for_generation(mock_db, user.id)

    no_pi_resp = make_profile_response(user.id).model_copy(update={"personal_info": None})
    pi, display_name = document_service.resolve_candidate_identity(no_pi_resp, user)
    assert pi.name == "Fallback User"
    assert display_name == "Fallback User"


@pytest.mark.asyncio
async def test_get_owned_download_and_delete(mock_db, tmp_path: Path):
    user = make_user(name="Alex")
    pdf_file = tmp_path / "doc.pdf"
    pdf_file.write_bytes(b"%PDF-1.4")
    cv = make_generated_cv(user_id=user.id, pdf_file_path=str(pdf_file), company_name="Acme")

    with patch("app.services.document_service.document_repo.get_owned_document", new=AsyncMock(return_value=None)):
        with pytest.raises(NotFoundError):
            await document_service.get_owned_document(mock_db, GeneratedCV, cv.id, user.id)

    profile = make_profile(user_id=user.id, personal_info={"name": "Alex Profile"})
    with (
        patch("app.services.document_service.document_repo.get_owned_document", new=AsyncMock(return_value=cv)),
        patch("app.services.document_service.profile_repo.get_by_user_id", new=AsyncMock(return_value=profile)),
    ):
        path, filename = await document_service.get_download_file_info(
            mock_db, GeneratedCV, cv.id, user, filename_prefix="cv"
        )
    assert path == str(pdf_file)
    assert filename == "cv-Acme-Alex-Profile.pdf"

    missing_cv = make_generated_cv(user_id=user.id, pdf_file_path=str(tmp_path / "missing.pdf"))
    with patch("app.services.document_service.document_repo.get_owned_document", new=AsyncMock(return_value=missing_cv)):
        with pytest.raises(NotFoundError, match="PDF file not found"):
            await document_service.get_download_file_info(
                mock_db, GeneratedCV, missing_cv.id, user, filename_prefix="cv"
            )

    with (
        patch("app.services.document_service.document_repo.get_owned_document", new=AsyncMock(return_value=cv)),
        patch("app.services.document_service.document_repo.delete_document", new=AsyncMock()) as mock_del,
        patch("app.services.document_service.delete_generated_document_file") as mock_unlink,
    ):
        await document_service.delete_owned_document(mock_db, GeneratedCV, cv.id, user.id)
    mock_del.assert_awaited_once_with(mock_db, cv)
    mock_unlink.assert_called_once_with(str(pdf_file), user.id)


@pytest.mark.asyncio
async def test_list_unified_documents_merges_sorts_and_paginates(mock_db):
    uid = uuid.uuid4()
    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = t1 + timedelta(hours=1)
    t3 = t1 + timedelta(hours=2)
    t4 = t1 + timedelta(hours=3)

    cv1 = make_generated_cv(user_id=uid, created_at=t1)
    cv2 = make_generated_cv(user_id=uid, created_at=t3)
    cl1 = make_generated_cover_letter(user_id=uid, created_at=t2)
    ce1 = make_generated_cold_email(user_id=uid, created_at=t4)

    async def _list_by_user(db, model_cls, user_id, *, limit, offset):
        if model_cls is GeneratedCV:
            return [cv2, cv1]
        if model_cls is GeneratedColdEmail:
            return [ce1]
        return [cl1]

    with patch("app.services.document_service.document_repo.list_by_user", side_effect=_list_by_user):
        page = await document_service.list_unified_documents(mock_db, uid, limit=3, offset=1)

    assert [item.id for item in page] == [cv2.id, cl1.id, cv1.id]
    assert [item.document_type for item in page] == ["cv", "cover_letter", "cv"]

    with patch("app.services.document_service.document_repo.list_by_user", side_effect=_list_by_user):
        ce_only = await document_service.list_unified_documents(
            mock_db, uid, document_type="cold_email", limit=10, offset=0
        )
    assert [item.id for item in ce_only] == [ce1.id]
    assert ce_only[0].document_type == "cold_email"
    assert ce_only[0].recruiter_name == ce1.recruiter_name
