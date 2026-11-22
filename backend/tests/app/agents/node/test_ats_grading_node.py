"""Unit tests for app.agents.node.ats_grading_node."""

from unittest.mock import patch

from app.agents.node.ats_grading_node import grade_cv_node, parse_cv_node
from tests.conftest import make_ats_check_result, make_parsed_cv_doc


def test_parse_cv_node():
    doc = make_parsed_cv_doc()
    with patch("app.agents.node.ats_grading_node.parse_cv_to_structured", return_value=doc):
        out = parse_cv_node({"raw_text": "cv text"})
    assert out["parsed_cv"] is doc

    with patch("app.agents.node.ats_grading_node.parse_cv_to_structured", side_effect=RuntimeError("boom")):
        err = parse_cv_node({"raw_text": "cv text"})
    assert "Failed to parse CV structure" in err["error"]


def test_grade_cv_node():
    missing = grade_cv_node({"parsed_cv": None})
    assert "missing" in missing["error"]

    doc = make_parsed_cv_doc()
    res = make_ats_check_result()
    with patch("app.agents.node.ats_grading_node.grade_parsed_cv", return_value=res) as mock_grade:
        out = grade_cv_node(
            {
                "parsed_cv": doc,
                "target_role": "SWE",
                "company_name": "Acme",
                "job_description": "Python APIs",
            }
        )
    assert out["result"] is res
    mock_grade.assert_called_once_with(
        doc,
        target_role="SWE",
        company_name="Acme",
        job_description="Python APIs",
    )

    with patch("app.agents.node.ats_grading_node.grade_parsed_cv", side_effect=RuntimeError("fail")):
        err = grade_cv_node({"parsed_cv": doc})
    assert "Failed to grade CV" in err["error"]
