"""Unit tests for app.schemas.profile."""

from app.schemas.profile import (
    PersonalInfo,
    ProfileResponse,
    ProfileUpdateRequest,
    SkillSet,
    _clean_optional_url,
    _sanitize_tag_list,
)
from tests.conftest import make_profile


def test_profile_schema_sanitizers_and_validators():
    tags = _sanitize_tag_list(["  Python\n ", "python", "FastAPI\x00", ""])
    assert tags == ["Python", "FastAPI"]

    assert _clean_optional_url("javascript:alert(1)") is None
    assert _clean_optional_url("github.com/alex") == "https://github.com/alex"
    assert _clean_optional_url("LinkedIn") == "LinkedIn"

    pi = PersonalInfo(name="<b>Alex</b>", email="a@b.com\x00")
    assert pi.name == "Alex"
    assert pi.email == "a@b.com"

    upd = ProfileUpdateRequest(summary="<p>Engineer</p>")
    assert upd.summary == "Engineer"

    skills = SkillSet(technical=["Python", "python", "Go"])
    assert skills.technical == ["Python", "Go"]

    orm_prof = make_profile(work_experiences=None, education=None)
    resp = ProfileResponse.model_validate(orm_prof)
    assert resp.work_experiences == []
    assert resp.education == []
