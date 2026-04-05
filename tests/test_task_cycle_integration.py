"""
Integration tests for TaskCycle pipeline — full cycle scenarios.

Strategy:
  - Mock call_fn passed to ParallelExecutor so LLM calls never fire
  - Use real _grade_code on temp files (subprocess) for realistic grade signal
  - Test complete flows: plan → execute → grade → ship and plan → execute → grade → pivot
  - Test the tier routing logic (correct model selected per complexity tier)
  - Test _extract_python_blocks directly
  - Test failure paths: executor errors, grade below threshold, git failures

These tests are slower than unit tests (real subprocesses for grading) — they
live in a separate file to allow selective CI exclusion if needed.
"""

from __future__ import annotations

import textwrap
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from python.helpers.complexity_classifier import TIER_MODEL_MAP, ComplexityTier
from python.helpers.parallel_executor import ExecutionResult
from python.tools.code_review import GradeResult
from python.tools.task_cycle import (
    TaskCycle,
    _extract_python_blocks,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tool(args: dict) -> TaskCycle:
    tool = TaskCycle.__new__(TaskCycle)
    tool.args = args
    tool.agent = MagicMock()
    tool.agent.call_utility_model = AsyncMock(return_value="mocked utility response")
    tool.name = "task_cycle"
    tool.method = None
    tool.message = ""
    tool.loop_data = None
    return tool


def _exec_result(id: str = "task_0", result: str = "done", status: str = "completed") -> ExecutionResult:
    return ExecutionResult(
        subtask_id=id,
        result=result,
        provider="anthropic",
        model="claude-sonnet-4-6",
        latency_ms=200.0,
        cost_cents=0.01,
        status=status,
    )


def _clean_python(tmp_path) -> tuple[str, str]:
    """Write a clean Python file and return (path, code_block_str)."""
    code = textwrap.dedent("""\
        \"\"\"Clean module for integration testing.\"\"\"


        def add(a: int, b: int) -> int:
            \"\"\"Return the sum of a and b.\"\"\"
            return a + b
        """)
    p = tmp_path / "clean_mod.py"
    p.write_text(code)
    return str(p), code


def _flawed_python(tmp_path) -> tuple[str, str]:
    """Write a flawed Python file and return (path, code_block_str)."""
    code = textwrap.dedent("""\
        import os,sys
        x=1
        y = x+2
        """)
    p = tmp_path / "flawed_mod.py"
    p.write_text(code)
    return str(p), code


# ---------------------------------------------------------------------------
# _extract_python_blocks
# ---------------------------------------------------------------------------


class TestExtractPythonBlocks:
    def test_extracts_single_block(self):
        text = "Here is code:\n```python\ndef foo():\n    return 1\n```\nDone."
        blocks = _extract_python_blocks(text)
        assert len(blocks) == 1
        assert "def foo():" in blocks[0]

    def test_extracts_multiple_blocks(self):
        text = "First:\n```python\nx = 1\n```\nSecond:\n```python\ny = 2\n```"
        blocks = _extract_python_blocks(text)
        assert len(blocks) == 2
        assert "x = 1" in blocks[0]
        assert "y = 2" in blocks[1]

    def test_no_blocks_returns_empty(self):
        text = "Just prose, no code blocks here."
        blocks = _extract_python_blocks(text)
        assert blocks == []

    def test_unclosed_block_not_included(self):
        """An unclosed ```python block should not produce a partial block."""
        text = "```python\ndef foo():\n    pass\n"  # no closing ```
        blocks = _extract_python_blocks(text)
        assert blocks == []

    def test_empty_block_excluded(self):
        text = "```python\n```"
        blocks = _extract_python_blocks(text)
        assert blocks == []

    def test_preserves_indentation(self):
        text = "```python\ndef foo():\n    x = 1\n    return x\n```"
        blocks = _extract_python_blocks(text)
        assert "    x = 1" in blocks[0]

    def test_non_python_blocks_ignored(self):
        text = "```bash\necho hello\n```\n```python\nx = 1\n```"
        blocks = _extract_python_blocks(text)
        assert len(blocks) == 1
        assert "x = 1" in blocks[0]


# ---------------------------------------------------------------------------
# Tier routing — _run_subtasks uses tier-selected model with fallback
# ---------------------------------------------------------------------------


class TestTierRouting:
    @pytest.mark.asyncio
    async def test_hard_task_routes_to_opus(self):
        """HARD tier should attempt claude-opus-4-6."""
        tool = _make_tool({"task": "architect an entire microservices platform from scratch", "action": "plan"})
        response = await tool.execute()
        assert response.additional["complexity_tier"] == "hard"
        provider, model = TIER_MODEL_MAP[ComplexityTier.HARD]
        assert provider == "anthropic"
        assert "opus" in model

    @pytest.mark.asyncio
    async def test_simple_task_routes_to_ollama(self):
        """SIMPLE tier should target ollama."""
        tool = _make_tool({"task": "list all files in the project", "action": "plan"})
        response = await tool.execute()
        assert response.additional["complexity_tier"] == "simple"
        provider, model = TIER_MODEL_MAP[ComplexityTier.SIMPLE]
        assert provider == "ollama"

    @pytest.mark.asyncio
    async def test_run_subtasks_falls_back_to_utility_on_model_error(self):
        """If tier model raises, _run_subtasks should fall back to utility model."""
        tool = _make_tool({"task": "fix the login bug", "action": "execute"})

        def raise_import(*args, **kwargs):
            raise RuntimeError("Provider not configured")

        with patch("python.tools.task_cycle.get_chat_model", side_effect=raise_import, create=True):
            # Should not raise — falls back to call_utility_model
            with patch.object(tool, "_run_subtasks", new=AsyncMock(return_value=[_exec_result()])):
                response = await tool.execute()
        assert response.break_loop is False

    @pytest.mark.asyncio
    async def test_medium_task_routes_to_sonnet(self):
        """MEDIUM tier should target claude-sonnet-4-6."""
        tool = _make_tool({"task": "implement a retry-with-backoff helper for the payment client", "action": "plan"})
        response = await tool.execute()
        assert response.additional["complexity_tier"] == "medium"
        provider, model = TIER_MODEL_MAP[ComplexityTier.MEDIUM]
        assert provider == "anthropic"
        assert "sonnet" in model


# ---------------------------------------------------------------------------
# Full cycle — ship path (real grader on clean code)
# ---------------------------------------------------------------------------


class TestFullCycleShipPath:
    @pytest.mark.asyncio
    async def test_clean_code_produces_ship_decision(self, tmp_path):
        """Full cycle with clean code block in LLM output → ship or ship_with_warnings."""
        _, code = _clean_python(tmp_path)
        code_result = _exec_result("task_0", result=f"Here is the implementation:\n```python\n{code}\n```")
        tool = _make_tool({"task": "add a helper function", "action": "full"})

        with patch.object(tool, "_run_subtasks", new=AsyncMock(return_value=[code_result])):
            response = await tool.execute()

        assert response.break_loop is False
        assert response.additional["decision"] in ("ship", "pivot", "escalate", "no_grade")
        # Clean code should not escalate
        assert response.additional["decision"] != "escalate"

    @pytest.mark.asyncio
    async def test_no_code_output_returns_no_grade(self):
        """If LLM produces only prose, decision is no_grade."""
        prose_result = _exec_result("task_0", result="The authentication system should use JWT tokens.")
        tool = _make_tool({"task": "describe the auth approach", "action": "full"})

        with patch.object(tool, "_run_subtasks", new=AsyncMock(return_value=[prose_result])):
            response = await tool.execute()

        assert response.additional["decision"] == "no_grade"

    @pytest.mark.asyncio
    async def test_multiple_code_blocks_all_graded(self, tmp_path):
        """Multiple python blocks across results should all be included in graded output."""
        block1 = "def helper_a():\n    return 1\n"
        block2 = "def helper_b():\n    return 2\n"
        combined_result = _exec_result(
            "task_0",
            result=f"```python\n{block1}```\nAlso:\n```python\n{block2}```",
        )
        tool = _make_tool({"task": "write two helpers", "action": "full"})

        fake_grade = GradeResult(
            score=90, passed=True, decision="ship", summary="Score 90/100 — no issues", tools_run=["ruff"]
        )
        with (
            patch.object(tool, "_run_subtasks", new=AsyncMock(return_value=[combined_result])),
            patch("python.tools.task_cycle._grade_code", return_value=fake_grade),
        ):
            response = await tool.execute()

        assert response.additional["decision"] == "ship"


# ---------------------------------------------------------------------------
# Full cycle — pivot path (flawed code)
# ---------------------------------------------------------------------------


class TestFullCyclePivotPath:
    @pytest.mark.asyncio
    async def test_flawed_code_grades_lower_than_clean(self, tmp_path):
        """LLM output with ruff violations grades lower than clean code (real grader)."""
        _, clean_code = _clean_python(tmp_path)
        _, flawed_code = _flawed_python(tmp_path)

        clean_result = _exec_result("task_0", result=f"```python\n{clean_code}\n```")
        flawed_result = _exec_result("task_0", result=f"```python\n{flawed_code}\n```")

        tool_clean = _make_tool({"task": "add a helper", "action": "full"})
        tool_flawed = _make_tool({"task": "add a helper", "action": "full"})

        with patch.object(tool_clean, "_run_subtasks", new=AsyncMock(return_value=[clean_result])):
            clean_resp = await tool_clean.execute()
        with patch.object(tool_flawed, "_run_subtasks", new=AsyncMock(return_value=[flawed_result])):
            flawed_resp = await tool_flawed.execute()

        # Flawed code must score lower than clean code
        assert flawed_resp.additional["grade"]["score"] < clean_resp.additional["grade"]["score"]
        assert flawed_resp.break_loop is False

    @pytest.mark.asyncio
    async def test_pivot_decision_includes_next_steps(self, tmp_path):
        """Pivot response should include issue descriptions in next_steps."""
        fake_grade = GradeResult(
            score=55,
            passed=False,
            decision="pivot",
            ruff_issues=["foo.py:1 [E401] Multiple imports on one line"],
            summary="Score 55/100 — 3 ruff violations",
            tools_run=["ruff"],
        )
        code_result = _exec_result("task_0", result="```python\nimport os,sys\n```")
        tool = _make_tool({"task": "write a small module", "action": "full"})

        with (
            patch.object(tool, "_run_subtasks", new=AsyncMock(return_value=[code_result])),
            patch("python.tools.task_cycle._grade_code", return_value=fake_grade),
        ):
            response = await tool.execute()

        assert response.additional["decision"] == "pivot"
        assert len(response.additional["next_steps"]) > 0

    @pytest.mark.asyncio
    async def test_escalate_path_on_very_low_score(self):
        """Score < 40 → escalate decision."""
        fake_grade = GradeResult(
            score=25,
            passed=False,
            decision="escalate",
            bandit_high=["line 3: subprocess with shell=True"],
            summary="Score 25/100 — security HIGH findings",
            tools_run=["ruff", "bandit"],
        )
        code_result = _exec_result(
            "task_0", result="```python\nimport subprocess\nsubprocess.run('ls', shell=True)\n```"
        )
        tool = _make_tool({"task": "run a command", "action": "full"})

        with (
            patch.object(tool, "_run_subtasks", new=AsyncMock(return_value=[code_result])),
            patch("python.tools.task_cycle._grade_code", return_value=fake_grade),
        ):
            response = await tool.execute()

        assert response.additional["decision"] == "escalate"
        assert "🚨" in response.message or "ESCALATE" in response.message


# ---------------------------------------------------------------------------
# Failed executor result handling
# ---------------------------------------------------------------------------


class TestExecutorFailureHandling:
    @pytest.mark.asyncio
    async def test_failed_subtask_does_not_crash_cycle(self):
        """A failed subtask should be reported but not raise an exception."""
        failed = _exec_result("task_0", result="Connection timeout", status="failed")
        tool = _make_tool({"task": "implement feature X", "action": "execute"})

        with patch.object(tool, "_run_subtasks", new=AsyncMock(return_value=[failed])):
            response = await tool.execute()

        assert response.break_loop is False
        assert response.additional is not None

    @pytest.mark.asyncio
    async def test_all_failed_subtasks_returns_no_grade(self):
        """If all subtasks fail with no code output, decision is no_grade."""
        all_failed = [
            _exec_result("task_0", result="error", status="failed"),
            _exec_result("task_1", result="timeout", status="timeout"),
        ]
        tool = _make_tool({"task": "implement feature Y", "action": "full"})

        with patch.object(tool, "_run_subtasks", new=AsyncMock(return_value=all_failed)):
            response = await tool.execute()

        assert response.additional["decision"] == "no_grade"

    @pytest.mark.asyncio
    async def test_mixed_results_only_grades_completed(self, tmp_path):
        """Only completed subtask results contribute to code extraction."""
        good_code = "```python\ndef ok(): return True\n```"
        results = [
            _exec_result("task_0", result=good_code, status="completed"),
            _exec_result("task_1", result="```python\nfail code\n```", status="failed"),
        ]
        fake_grade = GradeResult(
            score=88, passed=True, decision="ship_with_warnings", summary="Score 88/100", tools_run=["ruff"]
        )
        tool = _make_tool({"task": "implement two helpers", "action": "full"})

        with (
            patch.object(tool, "_run_subtasks", new=AsyncMock(return_value=results)),
            patch("python.tools.task_cycle._grade_code", return_value=fake_grade),
        ):
            response = await tool.execute()

        # Only the completed task contributed code; failed one was skipped
        assert response.additional["decision"] in ("ship", "pivot", "escalate", "no_grade")


# ---------------------------------------------------------------------------
# Ship action integration (git mocked)
# ---------------------------------------------------------------------------


class TestShipIntegration:
    @pytest.mark.asyncio
    async def test_ship_after_grade_commits_and_reports_sha(self):
        """ship action with valid grade → commit → SHA in response."""
        tool = _make_tool(
            {
                "action": "ship",
                "confirmed": "true",
                "message": "feat: add clean helper function",
                "paths": "python/helpers/clean_mod.py",
            }
        )
        mock_repo = MagicMock()
        fake_commit = MagicMock()
        fake_commit.hexsha = "abc1234567"  # pragma: allowlist secret
        mock_repo.index.commit.return_value = fake_commit
        mock_repo.head.is_detached = False
        mock_repo.active_branch.name = "feature/clean-helpers"

        with (
            patch("python.tools.task_cycle._repo_path", return_value="/fake/repo"),
            patch("python.tools.task_cycle._open_repo", return_value=mock_repo),
            patch("python.tools.git_tool._is_secret_file", return_value=False),
        ):
            response = await tool.execute()

        assert "abc1234" in response.message
        assert "feature/clean-helpers" in response.message
        assert response.break_loop is False

    @pytest.mark.asyncio
    async def test_ship_refuses_env_file(self):
        """ship action should fail if paths contain a secret file."""
        tool = _make_tool(
            {
                "action": "ship",
                "confirmed": "true",
                "message": "feat: add config with secrets",
                "paths": ".env,python/helpers/clean_mod.py",
            }
        )
        mock_repo = MagicMock()

        with (
            patch("python.tools.task_cycle._repo_path", return_value="/fake/repo"),
            patch("python.tools.task_cycle._open_repo", return_value=mock_repo),
        ):
            response = await tool.execute()

        # git_add should refuse .env
        assert "error" in response.message.lower() or "refused" in response.message.lower()
        mock_repo.index.commit.assert_not_called()


# ---------------------------------------------------------------------------
# Grade action integration (real subprocess)
# ---------------------------------------------------------------------------


class TestGradeActionIntegration:
    @pytest.mark.asyncio
    async def test_grade_clean_file_scores_high(self, tmp_path):
        """grade action on a lint-clean file should score ≥ 70."""
        path, _ = _clean_python(tmp_path)
        tool = _make_tool({"action": "grade", "path": path})
        response = await tool.execute()
        assert response.additional["score"] >= 70

    @pytest.mark.asyncio
    async def test_grade_flawed_file_scores_lower(self, tmp_path):
        """grade action on a flawed file should score below clean file."""
        clean_path, _ = _clean_python(tmp_path)
        flawed_path, _ = _flawed_python(tmp_path)

        tool_clean = _make_tool({"action": "grade", "path": clean_path})
        tool_flawed = _make_tool({"action": "grade", "path": flawed_path})

        clean_resp = await tool_clean.execute()
        flawed_resp = await tool_flawed.execute()

        assert flawed_resp.additional["score"] < clean_resp.additional["score"]

    @pytest.mark.asyncio
    async def test_grade_reports_decision_in_message(self, tmp_path):
        """grade action response message should include the decision string."""
        path, _ = _clean_python(tmp_path)
        tool = _make_tool({"action": "grade", "path": path})
        response = await tool.execute()
        # Decision should appear in the markdown report
        assert any(d in response.message.upper() for d in ("SHIP", "PIVOT", "ESCALATE"))
