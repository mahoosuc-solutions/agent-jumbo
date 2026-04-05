"""
Code Review Tool

Provides automated code quality analysis by running real static analysis tools
as subprocesses: ruff (lint), pytest (tests), mypy (type checking), bandit (security).

Grades output on a 0–100 composite score:
    90–100  SHIP   — auto-commit recommended
    70–89   SHIP*  — commit with warnings logged
    40–69   PIVOT  — return issues for agent revision
    0–39    ESCALATE — surface to human immediately
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field

from python.helpers.tool import Response, Tool

logger = logging.getLogger(__name__)

# Scoring weights (deductions from 100)
_RUFF_ISSUE_DEDUCTION = 3  # per ruff violation
_PYTEST_FAIL_DEDUCTION = 20  # flat deduction when tests fail
_MYPY_ERROR_DEDUCTION = 5  # per mypy error (capped)
_MYPY_ERROR_CAP = 30  # max deduction from mypy (avoids noise swamping)
_BANDIT_HIGH_DEDUCTION = 15  # per HIGH-severity bandit finding
_BANDIT_MEDIUM_DEDUCTION = 5  # per MEDIUM-severity bandit finding

# Grade thresholds
GRADE_SHIP = 90
GRADE_SHIP_WARN = 70
GRADE_PIVOT = 40


@dataclass
class GradeResult:
    score: int  # 0–100 composite
    passed: bool  # score >= GRADE_SHIP_WARN
    decision: str  # "ship" | "ship_with_warnings" | "pivot" | "escalate"
    ruff_issues: list[str] = field(default_factory=list)
    pytest_passed: bool = True
    pytest_output: str = ""
    mypy_errors: list[str] = field(default_factory=list)
    bandit_high: list[str] = field(default_factory=list)
    bandit_medium: list[str] = field(default_factory=list)
    summary: str = ""
    tools_run: list[str] = field(default_factory=list)

    def to_markdown(self, path: str) -> str:
        """Render GradeResult as a markdown report."""
        lines = [
            f"# Code Review: {path}",
            "",
            f"**Score**: {self.score}/100  |  **Decision**: `{self.decision.upper()}`",
            "",
        ]

        if self.ruff_issues:
            lines += ["## Ruff Issues", ""]
            for issue in self.ruff_issues[:20]:
                lines.append(f"- {issue}")
            if len(self.ruff_issues) > 20:
                lines.append(f"- … and {len(self.ruff_issues) - 20} more")
            lines.append("")

        if not self.pytest_passed:
            lines += ["## Test Failures", "", "```", self.pytest_output[:2000], "```", ""]

        if self.mypy_errors:
            lines += ["## Type Errors (mypy)", ""]
            for err in self.mypy_errors[:15]:
                lines.append(f"- {err}")
            lines.append("")

        if self.bandit_high or self.bandit_medium:
            lines += ["## Security (bandit)", ""]
            for w in self.bandit_high:
                lines.append(f"- 🔴 HIGH: {w}")
            for w in self.bandit_medium:
                lines.append(f"- 🟡 MEDIUM: {w}")
            lines.append("")

        lines += ["## Summary", "", self.summary or "No issues found.", ""]
        lines += ["---", f"*Tools run: {', '.join(self.tools_run)}*"]
        return "\n".join(lines)


def _run(cmd: list[str], cwd: str | None = None, timeout: int = 60) -> tuple[int, str, str]:
    """Run a subprocess and return (returncode, stdout, stderr)."""
    logger.debug("Running: %s (timeout=%ds)", " ".join(cmd), timeout)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        logger.warning("Command timed out after %ds: %s", timeout, " ".join(cmd))
        return 1, "", f"Command timed out after {timeout}s: {' '.join(cmd)}"
    except FileNotFoundError:
        logger.warning("Command not found: %s (install it or add to requirements.txt)", cmd[0])
        return 1, "", f"Command not found: {cmd[0]}"


def _find_test_file(source_path: str) -> str | None:
    """Infer test file path from source path (tests/test_{module}.py convention)."""
    basename = os.path.basename(source_path)
    module_name = os.path.splitext(basename)[0]

    # Try repo-root tests/ directory
    repo_root = source_path
    for _ in range(6):
        repo_root = os.path.dirname(repo_root)
        tests_dir = os.path.join(repo_root, "tests")
        if os.path.isdir(tests_dir):
            candidate = os.path.join(tests_dir, f"test_{module_name}.py")
            if os.path.exists(candidate):
                return candidate
            break
    return None


def _grade_code(path: str) -> GradeResult:
    """Run all four grader tools against *path* and produce a GradeResult.

    Scoring:
        Start at 100.
        - ruff: -3 per violation
        - pytest: -20 if tests fail (flat)
        - mypy: -5 per error (capped at -30)
        - bandit HIGH: -15 each; MEDIUM: -5 each
        Floor at 0.
    """
    score = 100
    tools_run: list[str] = []
    ruff_issues: list[str] = []
    pytest_passed = True
    pytest_output = ""
    mypy_errors: list[str] = []
    bandit_high: list[str] = []
    bandit_medium: list[str] = []

    # ------------------------------------------------------------------
    # 1. ruff check
    # ------------------------------------------------------------------
    rc, stdout, _stderr = _run(["ruff", "check", path, "--output-format=json"])
    tools_run.append("ruff")
    if stdout.strip():
        try:
            issues = json.loads(stdout)
            for issue in issues:
                code = issue.get("code", "?")
                msg = issue.get("message", "")
                loc = issue.get("location", {})
                row = loc.get("row", "?")
                ruff_issues.append(f"{path}:{row} [{code}] {msg}")
            score -= len(ruff_issues) * _RUFF_ISSUE_DEDUCTION
        except json.JSONDecodeError:
            # ruff exited non-zero but output is not JSON (parse error in source)
            ruff_issues.append(f"ruff parse error: {_stderr[:200]}")
            score -= _RUFF_ISSUE_DEDUCTION

    # ------------------------------------------------------------------
    # 2. pytest
    # ------------------------------------------------------------------
    test_file = _find_test_file(path)
    if test_file:
        rc, stdout, stderr = _run(["python", "-m", "pytest", test_file, "-q", "--tb=short"], timeout=120)
        tools_run.append("pytest")
        combined = (stdout + stderr).strip()
        if rc != 0:
            pytest_passed = False
            pytest_output = combined
            score -= _PYTEST_FAIL_DEDUCTION
    else:
        module_name = os.path.splitext(os.path.basename(path))[0]
        logger.info("pytest: skipped — no test file found for %s (expected tests/test_%s.py)", path, module_name)
        tools_run.append(f"pytest:skipped(no tests/test_{module_name}.py)")

    # ------------------------------------------------------------------
    # 3. mypy
    # ------------------------------------------------------------------
    rc, stdout, stderr = _run(["python", "-m", "mypy", path, "--ignore-missing-imports", "--no-error-summary"])
    tools_run.append("mypy")
    all_mypy = stdout + stderr
    for line in all_mypy.splitlines():
        # mypy error lines contain ": error:"
        if ": error:" in line:
            mypy_errors.append(line.strip())
    mypy_deduction = min(len(mypy_errors) * _MYPY_ERROR_DEDUCTION, _MYPY_ERROR_CAP)
    score -= mypy_deduction

    # ------------------------------------------------------------------
    # 4. bandit
    # ------------------------------------------------------------------
    rc, stdout, _stderr = _run(["bandit", "-r", path, "-f", "json", "-q"])
    tools_run.append("bandit")
    if stdout.strip():
        try:
            report = json.loads(stdout)
            for result in report.get("results", []):
                severity = result.get("issue_severity", "").upper()
                text = result.get("issue_text", "")
                line = result.get("line_number", "?")
                entry = f"line {line}: {text}"
                if severity == "HIGH":
                    bandit_high.append(entry)
                    score -= _BANDIT_HIGH_DEDUCTION
                elif severity == "MEDIUM":
                    bandit_medium.append(entry)
                    score -= _BANDIT_MEDIUM_DEDUCTION
        except json.JSONDecodeError:
            pass

    # ------------------------------------------------------------------
    # Compose result
    # ------------------------------------------------------------------
    score = max(0, score)
    passed = score >= GRADE_SHIP_WARN

    if score >= GRADE_SHIP:
        decision = "ship"
    elif score >= GRADE_SHIP_WARN:
        decision = "ship_with_warnings"
    elif score >= GRADE_PIVOT:
        decision = "pivot"
    else:
        decision = "escalate"

    summary_parts = []
    if ruff_issues:
        summary_parts.append(f"{len(ruff_issues)} ruff violations")
    if not pytest_passed:
        summary_parts.append("test failures")
    if mypy_errors:
        summary_parts.append(f"{len(mypy_errors)} type errors")
    if bandit_high:
        summary_parts.append(f"{len(bandit_high)} security HIGH findings")
    if bandit_medium:
        summary_parts.append(f"{len(bandit_medium)} security MEDIUM findings")

    summary = f"Score {score}/100 — " + (", ".join(summary_parts) if summary_parts else "no issues found")

    return GradeResult(
        score=score,
        passed=passed,
        decision=decision,
        ruff_issues=ruff_issues,
        pytest_passed=pytest_passed,
        pytest_output=pytest_output,
        mypy_errors=mypy_errors,
        bandit_high=bandit_high,
        bandit_medium=bandit_medium,
        summary=summary,
        tools_run=tools_run,
    )


def _grade_diff(diff: str) -> GradeResult:
    """Grade a git diff by writing changed Python files to temp and grading them."""
    import tempfile

    # Extract Python file content blocks from unified diff
    # Pattern: +++ b/{path} ... lines starting with +
    changed_files: dict[str, list[str]] = {}
    current_file: str | None = None

    for line in diff.splitlines():
        m = re.match(r"^\+\+\+ b/(.+\.py)$", line)
        if m:
            current_file = m.group(1)
            changed_files.setdefault(current_file, [])
        elif current_file and line.startswith("+") and not line.startswith("+++"):
            changed_files[current_file].append(line[1:])

    if not changed_files:
        return GradeResult(
            score=85,
            passed=True,
            decision="ship_with_warnings",
            summary="No Python files detected in diff — skipping static analysis",
            tools_run=[],
        )

    # Grade all changed Python files and merge results (worst score wins)
    worst: GradeResult | None = None
    for file_name, added_lines in changed_files.items():
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp:
            tmp.write("\n".join(added_lines))
            tmp_path = tmp.name
        try:
            result = _grade_code(tmp_path)
            result.summary = f"Diff review ({file_name}): {result.summary}"
            if worst is None or result.score < worst.score:
                worst = result
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    assert worst is not None  # changed_files is non-empty at this point
    return worst


class CodeReview(Tool):
    async def execute(self, **kwargs):
        """
        Perform automated code review using ruff, pytest, mypy, and bandit.

        Args (from self.args):
            file: File path to review (mutually exclusive with diff)
            diff: Git diff string to review (mutually exclusive with file)
            focus: Focus area (security/performance/style/all) — default: all

        Returns:
            Response with grade score, decision, and detailed findings.
        """
        file_path = self.args.get("file", "")
        diff = self.args.get("diff", "")
        focus = self.args.get("focus", "all").lower()

        if not file_path and not diff:
            return Response(
                message="Error: Either 'file' or 'diff' parameter is required. "
                'Examples: {"file": "src/main.py"} or {"diff": "git diff main...feature"}',
                break_loop=False,
            )

        valid_focuses = ["security", "performance", "style", "all"]
        if focus not in valid_focuses:
            return Response(
                message=f"Invalid focus: {focus}. Must be one of: {', '.join(valid_focuses)}",
                break_loop=False,
            )

        if file_path:
            if not os.path.exists(file_path):
                return Response(message=f"File not found: {file_path}", break_loop=False)
            grade = _grade_code(file_path)
            report = grade.to_markdown(file_path)
        else:
            grade = _grade_diff(diff)
            report = grade.to_markdown("git diff")

        return Response(
            message=report,
            break_loop=False,
            additional={
                "score": grade.score,
                "passed": grade.passed,
                "decision": grade.decision,
            },
        )
