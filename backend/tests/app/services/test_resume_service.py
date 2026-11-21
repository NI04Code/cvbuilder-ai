"""Unit tests for app.services.resume_service."""

import io
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from app.core.exceptions import BadRequestError, GenerationError
from app.schemas.profile import Certification, PersonalInfo, ResumeProfile, WorkExperience
from app.services import resume_service
from tests.conftest import make_profile


def test_date_sort_helpers():
    assert resume_service._parse_date_sort_key("Present") == (2, 9999, 12, 31)
    assert resume_service._parse_date_sort_key("2024-05-10") == (1, 2024, 5, 10)
    assert resume_service._parse_date_sort_key("03/2023") == (1, 2023, 3, 1)
    assert resume_service._parse_date_sort_key("Aug 2022") == (1, 2022, 8, 1)
    assert resume_service._parse_date_sort_key("2020") == (1, 2020, 1, 1)
    assert resume_service._parse_date_sort_key("unknown") == (0, 0, 0, 0)

    exps = [
        WorkExperience(company="Old", title="Dev", start_date="2020-01", end_date="2021-01"),
        WorkExperience(company="Curr", title="Lead", start_date="2023-01", end_date="Present"),
    ]
    assert [e.company for e in resume_service._sort_work_experiences_desc(exps)] == ["Curr", "Old"]

    certs = [
        Certification(name="C1", date="2021"),
        Certification(name="C2", date="2024-06"),
    ]
    assert [c.name for c in resume_service._sort_certifications_desc(certs)] == ["C2", "C1"]


@pytest.mark.asyncio
async def test_upload_and_parse_resume_success_and_cleanup(mock_db, tmp_path: Path):
    uid = uuid.uuid4()
    saved_file = tmp_path / "resume.pdf"
    saved_file.write_bytes(b"%PDF-1.4")
    upload = UploadFile(filename="resume.pdf", file=io.BytesIO(b"%PDF-1.4"))

    parsed = ResumeProfile(
        personal_info=PersonalInfo(name="Alex"),
        summary="Backend dev",
        work_experiences=[WorkExperience(company="Acme", title="Eng", start_date="2022-01", end_date="Present")],
        certifications=[Certification(name="AWS", date="2024-01")],
    )

    with (
        patch("app.services.resume_service.save_upload_file", new=AsyncMock(return_value=saved_file)),
        patch("app.services.resume_service.process_resume", new=AsyncMock(return_value={"raw_text": "raw", "profile": parsed})),
        patch("app.services.resume_service.profile_repo.get_by_user_id", new=AsyncMock(return_value=None)),
        patch(
            "app.services.resume_service.profile_repo.save_profile",
            new=AsyncMock(side_effect=lambda db, p, is_new=False: p),
        ),
    ):
        prof = await resume_service.upload_and_parse_resume(mock_db, uid, upload)
    assert prof.summary == "Backend dev"
    assert prof.source_file_path == str(saved_file)

    # Update existing profile branch
    existing = make_profile(user_id=uid)
    with (
        patch("app.services.resume_service.save_upload_file", new=AsyncMock(return_value=saved_file)),
        patch("app.services.resume_service.process_resume", new=AsyncMock(return_value={"raw_text": "raw2", "profile": parsed})),
        patch("app.services.resume_service.profile_repo.get_by_user_id", new=AsyncMock(return_value=existing)),
        patch(
            "app.services.resume_service.profile_repo.save_profile",
            new=AsyncMock(side_effect=lambda db, p, is_new=False: p),
        ),
    ):
        updated = await resume_service.upload_and_parse_resume(mock_db, uid, upload)
    assert updated.raw_resume_text == "raw2"

    # Error cleans up orphan file
    orphan = tmp_path / "orphan.pdf"
    orphan.write_bytes(b"%PDF-1.4")
    with (
        patch("app.services.resume_service.save_upload_file", new=AsyncMock(return_value=orphan)),
        patch("app.services.resume_service.process_resume", new=AsyncMock(return_value={"error": "LLM failed"})),
    ):
        with pytest.raises(GenerationError, match="LLM failed"):
            await resume_service.upload_and_parse_resume(mock_db, uid, upload)
    assert not orphan.exists()

    # Empty profile also cleans up
    orphan2 = tmp_path / "orphan2.pdf"
    orphan2.write_bytes(b"%PDF-1.4")
    with (
        patch("app.services.resume_service.save_upload_file", new=AsyncMock(return_value=orphan2)),
        patch("app.services.resume_service.process_resume", new=AsyncMock(return_value={"raw_text": "x", "profile": None})),
    ):
        with pytest.raises(GenerationError):
            await resume_service.upload_and_parse_resume(mock_db, uid, upload)
    assert not orphan2.exists()

    # save_upload_file errors: HTTPException passes through; generic wrapped in BadRequestError
    with patch("app.services.resume_service.save_upload_file", new=AsyncMock(side_effect=HTTPException(400, "bad"))):
        with pytest.raises(HTTPException):
            await resume_service.upload_and_parse_resume(mock_db, uid, upload)

    with patch("app.services.resume_service.save_upload_file", new=AsyncMock(side_effect=OSError("disk full"))):
        with pytest.raises(BadRequestError, match="disk full"):
            await resume_service.upload_and_parse_resume(mock_db, uid, upload)
