"""Unit tests for app.agents.node.cv_generation_node."""

from unittest.mock import MagicMock, patch

import pymupdf

from app.agents.node import cv_generation_node
from app.schemas.cv import CVGenerateRequest, SkillCategory
from tests.conftest import (
    make_ats_check_result,
    make_job_requirements,
    make_profile_response,
    make_tailored_cv,
)


def test_skill_helpers_and_enforce_single_row_skills():
    cv = make_tailored_cv(
        skills=[
            SkillCategory(
                category="Backend",
                items=["Python", "python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Redis", "GraphQL", "gRPC", "Kafka", "Celery", "Terraform"],
            )
        ]
    )
    non_skill_text = cv_generation_node._collect_non_skill_cv_text(cv)
    assert "Acme Corp" in non_skill_text
    assert cv_generation_node._is_skill_mentioned_elsewhere("Python", "Built Python APIs")
    assert not cv_generation_node._is_skill_mentioned_elsewhere("Rust", "Built Python APIs")

    reg, bold = pymupdf.Font("helv"), pymupdf.Font("hebo")
    width = cv_generation_node._measure_skill_row_width_pt("Backend", ["Python", "SQL"], reg, bold)
    assert width > 0

    with patch("app.agents.node.cv_generation_node._get_measurement_fonts", return_value=(reg, bold)):
        enforced = cv_generation_node._enforce_single_row_skills(cv)
    assert len(enforced.skills) == 1
    final_width = cv_generation_node._measure_skill_row_width_pt(
        enforced.skills[0].category, enforced.skills[0].items, reg, bold
    )
    assert final_width <= cv_generation_node._MAX_SKILL_ROW_WIDTH_PT


def test_generate_cv_node_and_score_cv_node():
    profile = make_profile_response()
    req = CVGenerateRequest(job_description="A" * 60, job_title="Backend Eng")
    reqs = make_job_requirements()
    cv = make_tailored_cv(ats_score=70.0)

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = cv
    with patch("app.agents.node.cv_generation_node.get_structured_llm", return_value=mock_llm):
        gen_out = cv_generation_node.generate_cv_node(
            {"profile": profile, "request": req, "job_requirements": reqs}
        )
    assert gen_out["tailored_cv"] is not None

    mock_llm.invoke.side_effect = RuntimeError("groq error")
    with patch("app.agents.node.cv_generation_node.get_structured_llm", return_value=mock_llm):
        err_out = cv_generation_node.generate_cv_node({"profile": profile, "request": req})
    assert "Failed to generate CV" in err_out["error"]

    # score_cv_node updates ats_score via grade_parsed_cv, and falls back gracefully on error
    with patch("app.agents.node.cv_generation_node.grade_parsed_cv", return_value=make_ats_check_result(overall_score=93)):
        scored = cv_generation_node.score_cv_node(
            {"tailored_cv": cv, "profile": profile, "request": req, "job_requirements": reqs}
        )
    assert scored["tailored_cv"].ats_score == 93.0

    with patch("app.agents.node.cv_generation_node.grade_parsed_cv", side_effect=RuntimeError("grade err")):
        fallback = cv_generation_node.score_cv_node(
            {"tailored_cv": cv, "profile": profile, "request": req, "job_requirements": reqs}
        )
    assert fallback["tailored_cv"].ats_score == 70.0
