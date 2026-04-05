"""
Tests for CodeReview tool — real grader with ruff, pytest, mypy, bandit.

Strategy:
  - GradeResult dataclass and to_markdown() are tested independently (no subprocess).
  - _grade_code() integration tests use real temp files to verify subprocess calls work.
  - CodeReview.execute() is tested with mocked _grade_code to keep the unit suite fast.
"""

from __future__ import annotations

import textwrap
from unittest.mock import MagicMock, patch

import pytest

from python.helpers.tool import Response
from python.tools.code_review import CodeReview, GradeResult, _find_test_file, _grade_code

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_clean_file(tmp_path) -> str:
    """Write a minimal, lint-clean Python file."""
    p = tmp_path / "clean_module.py"
    p.write_text(
        textwrap.dedent("""\
        \"\"\"A clean, minimal Python module.\"\"\"


        def add(a: int, b: int) -> int:
            \"\"\"Return the sum of a and b.\"\"\"
            return a + b
        """)
    )
    return str(p)


def _write_flawed_file(tmp_path) -> str:
    """Write a Python file with intentional ruff violations."""
    p = tmp_path / "flawed_module.py"
    p.write_text(
        textwrap.dedent("""\
        import os,sys
        x=1
        y = x+2
        """)
    )
    return str(p)


@pytest.fixture
def mock_agent():
    """Create mock agent"""
    agent = MagicMock()
    agent.agent_name = "test-agent"
    agent.context = MagicMock()
    agent.context.log = MagicMock()
    agent.context.log.log = MagicMock(return_value=MagicMock())
    agent.hist_add_tool_result = MagicMock()
    return agent


# ---------------------------------------------------------------------------
# GradeResult dataclass
# ---------------------------------------------------------------------------


class TestGradeResult:
    def test_to_markdown_includes_score(self):
        r = GradeResult(
            score=85,
            passed=True,
            decision="ship_with_warnings",
            summary="Score 85/100 — 3 ruff violations",
            tools_run=["ruff", "mypy"],
        )
        md = r.to_markdown("myfile.py")
        assert "85" in md
        assert "ship_with_warnings" in md.lower() or "SHIP_WITH_WARNINGS" in md

    def test_to_markdown_includes_ruff_issues(self):
        r = GradeResult(
            score=70,
            passed=True,
            decision="ship_with_warnings",
            ruff_issues=["myfile.py:3 [E302] Expected 2 blank lines"],
            tools_run=["ruff"],
        )
        md = r.to_markdown("myfile.py")
        assert "E302" in md

    def test_to_markdown_includes_test_failures(self):
        r = GradeResult(
            score=60,
            passed=False,
            decision="pivot",
            pytest_passed=False,
            pytest_output="FAILED test_foo.py::test_bar - AssertionError",
            tools_run=["pytest"],
        )
        md = r.to_markdown("foo.py")
        assert "AssertionError" in md

    def test_to_markdown_includes_bandit_findings(self):
        r = GradeResult(
            score=25,
            passed=False,
            decision="escalate",
            bandit_high=["line 5: subprocess call with shell=True"],
            tools_run=["bandit"],
        )
        md = r.to_markdown("risky.py")
        assert "HIGH" in md
        assert "subprocess" in md

    def test_to_markdown_has_summary_section(self):
        r = GradeResult(
            score=95,
            passed=True,
            decision="ship",
            summary="Score 95/100 — no issues found",
            tools_run=["ruff"],
        )
        md = r.to_markdown("good.py")
        assert "Summary" in md
        assert "no issues found" in md


# ---------------------------------------------------------------------------
# _grade_code — real subprocess integration
# ---------------------------------------------------------------------------


class TestGradeCodeCleanFile:
    def test_clean_file_scores_at_least_70(self, tmp_path):
        path = _write_clean_file(tmp_path)
        result = _grade_code(path)
        assert result.score >= 70, f"Expected >= 70, got {result.score}. Issues: {result.ruff_issues}"

    def test_clean_file_has_no_ruff_issues(self, tmp_path):
        path = _write_clean_file(tmp_path)
        result = _grade_code(path)
        assert result.ruff_issues == [], f"Expected no ruff issues, got: {result.ruff_issues}"

    def test_clean_file_passed_is_true(self, tmp_path):
        path = _write_clean_file(tmp_path)
        result = _grade_code(path)
        assert result.passed is True

    def test_clean_file_decision_is_ship(self, tmp_path):
        path = _write_clean_file(tmp_path)
        result = _grade_code(path)
        assert result.decision in ("ship", "ship_with_warnings")

    def test_tools_run_includes_ruff(self, tmp_path):
        path = _write_clean_file(tmp_path)
        result = _grade_code(path)
        assert "ruff" in result.tools_run


class TestGradeCodeFlawedFile:
    def test_flawed_file_has_ruff_issues(self, tmp_path):
        path = _write_flawed_file(tmp_path)
        result = _grade_code(path)
        assert len(result.ruff_issues) > 0, "Expected at least one ruff issue in flawed file"

    def test_flawed_file_scores_lower_than_clean(self, tmp_path):
        clean_path = _write_clean_file(tmp_path)
        flawed_path = _write_flawed_file(tmp_path)
        clean_result = _grade_code(clean_path)
        flawed_result = _grade_code(flawed_path)
        assert flawed_result.score < clean_result.score

    def test_score_is_bounded_0_to_100(self, tmp_path):
        path = _write_flawed_file(tmp_path)
        result = _grade_code(path)
        assert 0 <= result.score <= 100

    def test_summary_contains_score(self, tmp_path):
        path = _write_flawed_file(tmp_path)
        result = _grade_code(path)
        assert "Score" in result.summary


# ---------------------------------------------------------------------------
# _find_test_file helper
# ---------------------------------------------------------------------------


class TestFindTestFile:
    def test_finds_matching_test_file(self, tmp_path):
        source = tmp_path / "mymodule.py"
        source.write_text("x = 1")
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        test_file = tests_dir / "test_mymodule.py"
        test_file.write_text("def test_x(): assert 1 == 1")

        result = _find_test_file(str(source))
        assert result == str(test_file)

    def test_returns_none_when_no_test_file(self, tmp_path):
        source = tmp_path / "orphan_module.py"
        source.write_text("x = 1")
        result = _find_test_file(str(source))
        assert result is None


# ---------------------------------------------------------------------------
# CodeReview tool — execute() dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_code_review_tool_instantiates():
    agent = MagicMock()
    tool = CodeReview(
        agent=agent, name="code_review", method=None, args={"file": "example.py"}, message="Review code", loop_data=None
    )
    assert tool is not None


@pytest.mark.asyncio
async def test_code_review_requires_file_or_diff(mock_agent):
    tool = CodeReview(agent=mock_agent, name="code_review", method=None, args={}, message="Review code", loop_data=None)
    response = await tool.execute()
    assert isinstance(response, Response)
    assert "required" in response.message.lower()


@pytest.mark.asyncio
async def test_code_review_rejects_invalid_focus(mock_agent):
    tool = CodeReview(
        agent=mock_agent,
        name="code_review",
        method=None,
        args={"file": "test.py", "focus": "purple"},
        message="Review",
        loop_data=None,
    )
    response = await tool.execute()
    assert "Invalid focus" in response.message


@pytest.mark.asyncio
async def test_code_review_rejects_nonexistent_file(mock_agent):
    tool = CodeReview(
        agent=mock_agent,
        name="code_review",
        method=None,
        args={"file": "/nonexistent/path/file.py"},
        message="Review",
        loop_data=None,
    )
    response = await tool.execute()
    assert "not found" in response.message.lower()


@pytest.mark.asyncio
async def test_code_review_returns_grade_in_additional(tmp_path, mock_agent):
    """execute() returns grade score and decision in response.additional."""
    path = _write_clean_file(tmp_path)
    fake_grade = GradeResult(
        score=92,
        passed=True,
        decision="ship",
        summary="Score 92/100 — no issues found",
        tools_run=["ruff", "pytest", "mypy", "bandit"],
    )
    tool = CodeReview(
        agent=mock_agent,
        name="code_review",
        method=None,
        args={"file": path},
        message="Review",
        loop_data=None,
    )
    with patch("python.tools.code_review._grade_code", return_value=fake_grade):
        response = await tool.execute()

    assert response.additional is not None
    assert response.additional["score"] == 92
    assert response.additional["decision"] == "ship"
    assert response.break_loop is False


@pytest.mark.asyncio
async def test_code_review_accepts_diff_returns_response(mock_agent):
    """execute() with a diff string returns a valid Response."""
    fake_grade = GradeResult(
        score=80,
        passed=True,
        decision="ship_with_warnings",
        summary="Score 80/100",
        tools_run=[],
    )
    tool = CodeReview(
        agent=mock_agent,
        name="code_review",
        method=None,
        args={"diff": "--- a/foo.py\n+++ b/foo.py\n@@ -1 +1 @@\n-x = 1\n+x = 2"},
        message="Review diff",
        loop_data=None,
    )
    with patch("python.tools.code_review._grade_diff", return_value=fake_grade):
        response = await tool.execute()

    assert isinstance(response, Response)
    assert response.break_loop is False
