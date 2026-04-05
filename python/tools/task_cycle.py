"""
Task Cycle Tool — end-to-end agentic pipeline: plan → execute → grade → ship or pivot.

Actions:
    plan     — decompose task to plan, return steps with model assignments (no execution)
    execute  — decompose + dispatch subtasks via LLM (no grade/ship)
    grade    — grade existing file at given path
    full     — plan + execute + grade + ship decision (default)
    ship     — commit after human approves a prior grading (requires confirmed=true)

Pipeline (full action):
    1. ComplexityClassifier.score(task)  → tier, token_budget, model
    2. TaskDecomposer.decompose_simple() → list[SubTask]
    3. ParallelExecutor.execute()        → list[ExecutionResult]
    4. CodeReview._grade_code()          → GradeResult (if code output detected)
    5. ShipDecision                      → ship / pivot / escalate
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any

from python.helpers.complexity_classifier import TIER_MODEL_MAP, ComplexityClassifier, ComplexityTier
from python.helpers.parallel_executor import ExecutionResult, ParallelExecutor
from python.helpers.task_decomposer import SubTask, TaskDecomposer
from python.helpers.tool import Response, Tool
from python.tools.code_review import _grade_code
from python.tools.git_tool import _open_repo, _repo_path

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class PlannedStep:
    id: str
    description: str
    type: str  # SubTaskType.value
    provider: str
    model: str | None
    depends_on: list[str] = field(default_factory=list)


@dataclass
class CycleResult:
    decision: str  # ship | pivot | escalate | no_grade
    task: str
    complexity_tier: str
    confidence: float
    steps: list[PlannedStep]
    execution_results: list[dict[str, Any]] = field(default_factory=list)
    grade: dict[str, Any] | None = None
    commit_sha: str | None = None
    next_steps: list[str] = field(default_factory=list)
    elapsed_ms: float = 0.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _subtask_to_planned_step(st: SubTask, tier: ComplexityTier) -> PlannedStep:
    """Map a SubTask to a PlannedStep with tier-resolved model."""
    provider, model = TIER_MODEL_MAP[tier]
    return PlannedStep(
        id=st.id,
        description=st.prompt[:120],
        type=st.type.value,
        provider=provider,
        model=model,
        depends_on=list(st.dependencies),
    )


def _ship_decision(grade_result, results: list[ExecutionResult]) -> tuple[str, list[str]]:
    """Map a GradeResult to a (decision, next_steps) pair."""
    score = grade_result.score
    if score >= 90:
        return "ship", [f"Score {score}/100 — auto-commit recommended"]
    if score >= 70:
        issues = grade_result.ruff_issues[:3] + grade_result.mypy_errors[:3]
        return "ship", [f"Score {score}/100 — shipped with warnings"] + [f"  - {i}" for i in issues]
    if score >= 40:
        issues = (
            [f"ruff: {i}" for i in grade_result.ruff_issues[:5]]
            + [f"mypy: {e}" for e in grade_result.mypy_errors[:3]]
            + [f"bandit: {b}" for b in grade_result.bandit_high[:2]]
        )
        return "pivot", [f"Score {score}/100 — revise before committing", *issues]
    steps = [f"Score {score}/100 — critical issues, human review required"]
    steps += [f"bandit HIGH: {b}" for b in grade_result.bandit_high]
    if not grade_result.pytest_passed:
        steps.append(f"test failure: {grade_result.pytest_output[:200]}")
    return "escalate", steps


# ---------------------------------------------------------------------------
# TaskCycle Tool
# ---------------------------------------------------------------------------


class TaskCycle(Tool):
    """Full agentic task cycle: plan → execute → grade → ship or pivot."""

    async def execute(self, **kwargs) -> Response:
        task = self.args.get("task", "").strip()
        action = self.args.get("action", "full").lower().strip()

        valid_actions = {"plan", "execute", "grade", "full", "ship"}
        if action not in valid_actions:
            return Response(
                message=f"Unknown action: {action!r}. Allowed: {', '.join(sorted(valid_actions))}",
                break_loop=False,
            )

        if action == "ship":
            return await self._action_ship()

        if action == "grade":
            return await self._action_grade()

        if not task:
            return Response(
                message="Missing `task` argument. Usage: task_cycle(task='...', action='full')",
                break_loop=False,
            )

        t0 = time.monotonic()

        # 1. Classify complexity
        complexity = ComplexityClassifier.score(task)

        # 2. Decompose
        decomposer = TaskDecomposer()
        subtasks = decomposer.decompose_simple(task)

        # Build planned steps with tier-resolved models
        steps = [_subtask_to_planned_step(st, complexity.tier) for st in subtasks]

        if action == "plan":
            return self._format_plan(task, complexity, steps)

        # 3. Execute subtasks
        exec_results = await self._run_subtasks(subtasks, complexity)

        if action == "execute":
            elapsed = (time.monotonic() - t0) * 1000
            return self._format_execute(task, complexity, steps, exec_results, elapsed)

        # 4. Full: grade + ship decision
        result = await self._full_cycle(task, complexity, steps, exec_results, t0)
        return self._format_full(result)

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    def _format_plan(self, task: str, complexity, steps: list[PlannedStep]) -> Response:
        lines = [
            "## Task Plan",
            "",
            f"**Task:** {task}",
            f"**Complexity:** `{complexity.tier.value}` (confidence {complexity.confidence:.0%})",
            f"**Reason:** {complexity.reason}",
            f"**Recommended model:** {complexity.recommended_provider}/{complexity.recommended_model}",
            f"**Estimated subtasks:** {complexity.estimated_subtasks}",
            f"**Token budget:** {complexity.token_budget:,}",
            "",
            f"### Steps ({len(steps)})",
            "",
        ]
        for step in steps:
            deps = f" (after: {', '.join(step.depends_on)})" if step.depends_on else ""
            lines.append(f"- **{step.id}** [{step.type}] → `{step.provider}/{step.model}`{deps}")
            lines.append(f"  > {step.description}")
        message = "\n".join(lines)
        additional = {
            "task": task,
            "complexity_tier": complexity.tier.value,
            "confidence": complexity.confidence,
            "steps": [asdict(s) for s in steps],
        }
        return Response(message=message, break_loop=False, additional=additional)

    def _format_execute(
        self,
        task: str,
        complexity,
        steps: list[PlannedStep],
        results: list[ExecutionResult],
        elapsed_ms: float,
    ) -> Response:
        lines = ["## Execution Complete", "", f"**Task:** {task}", ""]
        for r in results:
            status = "OK" if r.status == "completed" else "FAIL"
            lines.append(f"- `{r.subtask_id}` [{r.provider}] {status} ({r.latency_ms:.0f}ms)")
            if r.result:
                preview = r.result[:200].replace("\n", " ")
                lines.append(f"  > {preview}…")
        lines += ["", f"*Elapsed: {elapsed_ms:.0f}ms — {len(results)} subtasks*"]
        return Response(
            message="\n".join(lines),
            break_loop=False,
            additional={
                "task": task,
                "complexity_tier": complexity.tier.value,
                "subtask_count": len(results),
                "elapsed_ms": elapsed_ms,
                "results": [asdict(r) for r in results],
            },
        )

    async def _action_grade(self) -> Response:
        path = self.args.get("path", "").strip()
        if not path:
            return Response(message="Missing `path` argument for grade action.", break_loop=False)
        import os

        if not os.path.exists(path):
            return Response(message=f"File not found: {path}", break_loop=False)
        grade = _grade_code(path)
        return Response(
            message=grade.to_markdown(path),
            break_loop=False,
            additional={"score": grade.score, "passed": grade.passed, "decision": grade.decision},
        )

    async def _action_ship(self) -> Response:
        confirmed_raw = self.args.get("confirmed", "false").lower()
        confirmed = confirmed_raw in ("true", "1", "yes")
        if not confirmed:
            return Response(
                message="Ship action requires `confirmed=true`. Review the grade report before proceeding.",
                break_loop=False,
            )
        message = self.args.get("message", "").strip()
        if not message:
            return Response(message="Ship action requires a `message` (commit message).", break_loop=False)
        paths_raw = self.args.get("paths", "")
        paths = [p.strip() for p in paths_raw.split(",") if p.strip()]
        if not paths:
            return Response(
                message="Ship action requires `paths` (comma-separated file paths to commit).", break_loop=False
            )

        from python.tools.git_tool import git_add, git_commit

        try:
            repo = _open_repo(_repo_path())
        except Exception as exc:
            return Response(message=f"Failed to open git repository: {exc}", break_loop=False)

        add_result = git_add(repo, paths)
        if add_result["status"] == "error":
            return Response(message=f"Git add failed: {add_result['error']}", break_loop=False)

        commit_result = git_commit(repo, message)
        if commit_result["status"] == "error":
            return Response(message=f"Git commit failed: {commit_result['error']}", break_loop=False)

        sha = commit_result["sha"]
        branch = commit_result["branch"]
        return Response(
            message=f"Shipped: committed `{sha}` on `{branch}`\n\n> {message}\n\nRun `git_tool(action='push', confirmed='true')` to push to remote.",
            break_loop=False,
            additional={"sha": sha, "branch": branch, "message": message},
        )

    # ------------------------------------------------------------------
    # Full cycle internals
    # ------------------------------------------------------------------

    async def _run_subtasks(self, subtasks: list[SubTask], complexity) -> list[ExecutionResult]:
        """Dispatch subtasks via ParallelExecutor using agent's utility model."""
        executor = ParallelExecutor(timeout_seconds=120)

        async def call_fn(prompt: str, provider: str, model: str | None) -> str:
            from python.helpers.call_llm import call_llm

            llm = self.agent.config.utility_model.create_model()
            return await call_llm(
                system="You are a helpful assistant. Complete the following task concisely.",
                model=llm,
                message=prompt,
            )

        return await executor.execute(subtasks, call_fn)

    async def _full_cycle(
        self,
        task: str,
        complexity,
        steps: list[PlannedStep],
        exec_results: list[ExecutionResult],
        t0: float,
    ) -> CycleResult:
        elapsed = (time.monotonic() - t0) * 1000

        # Attempt to grade code output if any subtask produced Python code
        grade_dict: dict[str, Any] | None = None
        decision = "no_grade"
        next_steps: list[str] = []

        code_output = self._extract_code_output(exec_results)
        if code_output:
            import os
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp:
                tmp.write(code_output)
                tmp_path = tmp.name
            try:
                grade = _grade_code(tmp_path)
                grade_dict = {
                    "score": grade.score,
                    "passed": grade.passed,
                    "decision": grade.decision,
                    "summary": grade.summary,
                }
                decision, next_steps = _ship_decision(grade, exec_results)
            finally:
                os.unlink(tmp_path)
        else:
            # No code to grade — surface results for human review
            decision = "no_grade"
            next_steps = [
                "Review execution output above",
                "Run task_cycle(action='grade', path='...') if code was written",
            ]

        return CycleResult(
            decision=decision,
            task=task,
            complexity_tier=complexity.tier.value,
            confidence=complexity.confidence,
            steps=steps,
            execution_results=[asdict(r) for r in exec_results],
            grade=grade_dict,
            next_steps=next_steps,
            elapsed_ms=elapsed,
        )

    def _extract_code_output(self, results: list[ExecutionResult]) -> str | None:
        """Return combined Python code from results that contain code blocks."""
        code_lines: list[str] = []
        in_block = False
        for r in results:
            if r.status != "completed":
                continue
            for line in r.result.splitlines():
                if line.strip().startswith("```python"):
                    in_block = True
                    continue
                if in_block and line.strip() == "```":
                    in_block = False
                    continue
                if in_block:
                    code_lines.append(line)
        return "\n".join(code_lines) if code_lines else None

    def _format_full(self, result: CycleResult) -> Response:
        decision_emoji = {"ship": "✅", "pivot": "🔄", "escalate": "🚨", "no_grade": "📋"}.get(result.decision, "?")
        lines = [
            f"## Task Cycle Complete {decision_emoji}",
            "",
            f"**Task:** {result.task}",
            f"**Complexity:** `{result.complexity_tier}` (confidence {result.confidence:.0%})",
            f"**Decision:** `{result.decision.upper()}`",
        ]

        if result.grade:
            lines += [
                f"**Grade:** {result.grade['score']}/100 — {result.grade['summary']}",
            ]

        lines += ["", f"### Subtasks ({len(result.execution_results)})", ""]
        for r in result.execution_results:
            status = "OK" if r.get("status") == "completed" else "FAIL"
            lines.append(f"- `{r.get('subtask_id')}` [{r.get('provider')}] {status} ({r.get('latency_ms', 0):.0f}ms)")

        if result.next_steps:
            lines += ["", "### Next Steps", ""]
            for step in result.next_steps:
                lines.append(f"- {step}")

        lines += ["", f"*Elapsed: {result.elapsed_ms:.0f}ms*"]

        return Response(
            message="\n".join(lines),
            break_loop=False,
            additional=asdict(result),
        )
