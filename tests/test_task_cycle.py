"""
Tests for TaskCycle — end-to-end agentic pipeline tool.

Strategy:
  - Mock call_llm and _grade_code to keep the suite fast and deterministic.
  - Test each action independently: plan, execute, grade, full, ship.
  - Assert structured `additional` dict contains expected fields.
"""

from __future__ import annotations

from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from python.helpers.complexity_classifier import ComplexityTier
from python.helpers.parallel_executor import ExecutionResult
from python.tools.code_review import GradeResult
from python.tools.task_cycle import (
    CycleResult,
    TaskCycle,
    _ship_decision,
    _subtask_to_planned_step,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tool(args: dict) -> TaskCycle:
    """Build a TaskCycle without a real Agent."""
    tool = TaskCycle.__new__(TaskCycle)
    tool.args = args
    tool.agent = MagicMock()
    tool.agent.config.utility_model.create_model.return_value = MagicMock()
    tool.name = "task_cycle"
    tool.method = None
    tool.message = ""
    tool.loop_data = None
    return tool


def _make_exec_result(id: str = "task_0", result: str = "done", status: str = "completed") -> ExecutionResult:
    return ExecutionResult(
        subtask_id=id,
        result=result,
        provider="anthropic",
        model="claude-sonnet-4-6",
        latency_ms=250.0,
        cost_cents=0.01,
        status=status,
    )


def _make_grade(score: int, decision: str) -> GradeResult:
    return GradeResult(
        score=score,
        passed=score >= 70,
        decision=decision,
        summary=f"Score {score}/100 — test grade",
        tools_run=["ruff", "mypy"],
    )


# ---------------------------------------------------------------------------
# _subtask_to_planned_step
# ---------------------------------------------------------------------------


class TestSubtaskToPlannedStep:
    def test_maps_hard_tier_to_opus(self):
        from python.helpers.task_decomposer import SubTask, SubTaskType

        st = SubTask(
            id="t0", type=SubTaskType.GENERATE, prompt="write a full platform", recommended_provider="anthropic"
        )
        step = _subtask_to_planned_step(st, ComplexityTier.HARD)
        assert step.provider == "anthropic"
        assert "opus" in step.model

    def test_maps_simple_tier_to_ollama(self):
        from python.helpers.task_decomposer import SubTask, SubTaskType

        st = SubTask(id="t0", type=SubTaskType.RESEARCH, prompt="list files", recommended_provider="google")
        step = _subtask_to_planned_step(st, ComplexityTier.SIMPLE)
        assert step.provider == "ollama"

    def test_description_truncated_to_120_chars(self):
        from python.helpers.task_decomposer import SubTask, SubTaskType

        long_prompt = "x" * 200
        st = SubTask(id="t0", type=SubTaskType.GENERATE, prompt=long_prompt, recommended_provider="anthropic")
        step = _subtask_to_planned_step(st, ComplexityTier.MEDIUM)
        assert len(step.description) == 120


# ---------------------------------------------------------------------------
# _ship_decision
# ---------------------------------------------------------------------------


class TestShipDecision:
    def test_score_90_returns_ship(self):
        grade = _make_grade(92, "ship")
        decision, steps = _ship_decision(grade, [])
        assert decision == "ship"
        assert any("92" in s for s in steps)

    def test_score_75_returns_ship(self):
        grade = _make_grade(75, "ship_with_warnings")
        decision, steps = _ship_decision(grade, [])
        assert decision == "ship"

    def test_score_55_returns_pivot(self):
        grade = _make_grade(55, "pivot")
        decision, steps = _ship_decision(grade, [])
        assert decision == "pivot"
        assert any("revise" in s for s in steps)

    def test_score_30_returns_escalate(self):
        grade = _make_grade(30, "escalate")
        decision, steps = _ship_decision(grade, [])
        assert decision == "escalate"
        assert any("human review" in s for s in steps)


# ---------------------------------------------------------------------------
# TaskCycle.execute() — unknown action
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_action_returns_error():
    tool = _make_tool({"task": "build something", "action": "teleport"})
    response = await tool.execute()
    assert "Unknown action" in response.message
    assert response.break_loop is False


@pytest.mark.asyncio
async def test_missing_task_returns_error():
    tool = _make_tool({"action": "full"})
    response = await tool.execute()
    assert "Missing" in response.message


# ---------------------------------------------------------------------------
# plan action
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plan_action_returns_steps():
    tool = _make_tool({"task": "add a user authentication endpoint", "action": "plan"})
    response = await tool.execute()
    assert response.break_loop is False
    assert response.additional is not None
    assert "steps" in response.additional
    assert len(response.additional["steps"]) >= 1
    assert "complexity_tier" in response.additional


@pytest.mark.asyncio
async def test_plan_action_includes_model_info():
    tool = _make_tool({"task": "architect an entire microservices platform", "action": "plan"})
    response = await tool.execute()
    assert "Complexity" in response.message
    assert "provider" in response.message or "model" in response.message or "anthropic" in response.message.lower()


@pytest.mark.asyncio
async def test_plan_action_no_execution():
    """plan action must NOT call call_llm."""
    tool = _make_tool({"task": "fix the login bug", "action": "plan"})
    with patch("python.tools.task_cycle.ParallelExecutor") as mock_exec:
        response = await tool.execute()
    mock_exec.assert_not_called()
    assert response.break_loop is False


# ---------------------------------------------------------------------------
# grade action
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_grade_action_missing_path():
    tool = _make_tool({"action": "grade"})
    response = await tool.execute()
    assert "Missing" in response.message


@pytest.mark.asyncio
async def test_grade_action_nonexistent_file(tmp_path):
    # Path must be inside repo root to pass traversal guard, but not exist as a file
    repo_root = str(tmp_path)
    nonexistent = str(tmp_path / "nonexistent.py")
    tool = _make_tool({"action": "grade", "path": nonexistent})
    with patch("python.tools.task_cycle._repo_path", return_value=repo_root):
        response = await tool.execute()
    assert "not found" in response.message.lower() or "does not exist" in response.message.lower()


@pytest.mark.asyncio
async def test_grade_action_returns_score(tmp_path):
    p = tmp_path / "sample.py"
    p.write_text('"""Sample."""\n\ndef hello() -> str:\n    return "hello"\n')
    repo_root = str(tmp_path)
    fake_grade = _make_grade(88, "ship_with_warnings")
    tool = _make_tool({"action": "grade", "path": str(p)})
    with (
        patch("python.tools.task_cycle._repo_path", return_value=repo_root),
        patch("python.tools.task_cycle._grade_code", return_value=fake_grade),
    ):
        response = await tool.execute()
    assert response.additional is not None
    assert response.additional["score"] == 88
    assert response.additional["decision"] == "ship_with_warnings"


# ---------------------------------------------------------------------------
# ship action
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ship_requires_confirmed():
    tool = _make_tool({"action": "ship", "message": "feat: add tests", "paths": "src/main.py"})
    response = await tool.execute()
    assert "confirmed" in response.message.lower()


@pytest.mark.asyncio
async def test_ship_requires_message():
    tool = _make_tool({"action": "ship", "confirmed": "true", "paths": "src/main.py"})
    response = await tool.execute()
    assert "message" in response.message.lower()


@pytest.mark.asyncio
async def test_ship_requires_paths():
    tool = _make_tool({"action": "ship", "confirmed": "true", "message": "feat: add auth"})
    response = await tool.execute()
    assert "paths" in response.message.lower()


@pytest.mark.asyncio
async def test_ship_with_confirmed_adds_and_commits():
    tool = _make_tool(
        {
            "action": "ship",
            "confirmed": "true",
            "message": "feat: add authentication layer",
            "paths": "src/auth.py",
        }
    )
    mock_repo = MagicMock()
    fake_commit = MagicMock()
    fake_commit.hexsha = "abc1234567"  # pragma: allowlist secret
    mock_repo.index.commit.return_value = fake_commit
    mock_repo.head.is_detached = False
    mock_repo.active_branch.name = "main"

    with (
        patch("python.tools.task_cycle._repo_path", return_value="/fake/repo"),
        patch("python.tools.task_cycle._open_repo", return_value=mock_repo),
        patch("python.tools.git_tool._is_secret_file", return_value=False),
    ):
        response = await tool.execute()

    assert "Shipped" in response.message or "abc1234" in response.message
    assert response.break_loop is False


# ---------------------------------------------------------------------------
# full action (mocked LLM + grader)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_action_returns_structured_decision():
    tool = _make_tool({"task": "add a health check endpoint", "action": "full"})
    fake_exec_result = _make_exec_result("task_0", result="def health_check(): return {'status': 'ok'}")
    fake_grade = _make_grade(82, "ship_with_warnings")

    with (
        patch.object(tool, "_run_subtasks", new=AsyncMock(return_value=[fake_exec_result])),
        patch("python.tools.task_cycle._grade_code", return_value=fake_grade),
    ):
        response = await tool.execute()

    assert response.break_loop is False
    assert response.additional is not None
    assert "decision" in response.additional
    assert "complexity_tier" in response.additional
    assert response.additional["decision"] in ("ship", "pivot", "escalate", "no_grade")


@pytest.mark.asyncio
async def test_full_action_no_code_returns_no_grade():
    """When subtasks produce no Python code, decision should be no_grade."""
    tool = _make_tool({"task": "summarize the project", "action": "full"})
    fake_exec_result = _make_exec_result("task_0", result="The project is an agentic platform.")

    with patch.object(tool, "_run_subtasks", new=AsyncMock(return_value=[fake_exec_result])):
        response = await tool.execute()

    assert response.additional["decision"] == "no_grade"


@pytest.mark.asyncio
async def test_full_action_escalates_on_low_score():
    tool = _make_tool({"task": "implement feature X", "action": "full"})
    python_code = "```python\nimport subprocess\nsubprocess.run('rm -rf /', shell=True)\n```"
    fake_exec_result = _make_exec_result("task_0", result=python_code)
    fake_grade = _make_grade(20, "escalate")

    with (
        patch.object(tool, "_run_subtasks", new=AsyncMock(return_value=[fake_exec_result])),
        patch("python.tools.task_cycle._grade_code", return_value=fake_grade),
    ):
        response = await tool.execute()

    assert response.additional["decision"] == "escalate"


@pytest.mark.asyncio
async def test_full_action_message_contains_decision():
    tool = _make_tool({"task": "refactor the auth module", "action": "full"})
    fake_exec_result = _make_exec_result("task_0", result="```python\ndef auth(): pass\n```")
    fake_grade = _make_grade(92, "ship")

    with (
        patch.object(tool, "_run_subtasks", new=AsyncMock(return_value=[fake_exec_result])),
        patch("python.tools.task_cycle._grade_code", return_value=fake_grade),
    ):
        response = await tool.execute()

    assert "SHIP" in response.message or "ship" in response.message.lower()


# ---------------------------------------------------------------------------
# execute action (mocked LLM only)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_action_runs_subtasks():
    tool = _make_tool({"task": "write a login function", "action": "execute"})
    fake_exec_result = _make_exec_result("task_0", result="def login(user, pw): ...")

    with patch.object(tool, "_run_subtasks", new=AsyncMock(return_value=[fake_exec_result])):
        response = await tool.execute()

    assert response.break_loop is False
    assert response.additional is not None
    assert response.additional["subtask_count"] == 1


@pytest.mark.asyncio
async def test_execute_action_no_grade():
    """Execute action should NOT call _grade_code."""
    tool = _make_tool({"task": "write tests for auth module", "action": "execute"})
    fake_result = _make_exec_result("task_0", result="# tests written")

    with (
        patch.object(tool, "_run_subtasks", new=AsyncMock(return_value=[fake_result])),
        patch("python.tools.task_cycle._grade_code") as mock_grade,
    ):
        await tool.execute()

    mock_grade.assert_not_called()


# ---------------------------------------------------------------------------
# CycleResult dataclass
# ---------------------------------------------------------------------------


class TestCycleResult:
    def test_asdict_includes_all_fields(self):
        result = CycleResult(
            decision="ship",
            task="add tests",
            complexity_tier="easy",
            confidence=0.8,
            steps=[],
        )
        d = asdict(result)
        assert d["decision"] == "ship"
        assert d["complexity_tier"] == "easy"
        assert d["grade"] is None
        assert d["commit_sha"] is None

    def test_grade_field_holds_dict(self):
        result = CycleResult(
            decision="pivot",
            task="refactor",
            complexity_tier="medium",
            confidence=0.6,
            steps=[],
            grade={"score": 55, "passed": False, "decision": "pivot", "summary": "test"},
        )
        assert result.grade["score"] == 55
