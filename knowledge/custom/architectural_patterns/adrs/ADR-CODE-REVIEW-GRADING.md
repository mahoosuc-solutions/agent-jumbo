# ADR: Code Review Grading — Real Subprocess Tool Chain

## Status

Accepted

## Context

The original `code_review.py` was a stub that returned hardcoded template responses
regardless of file content. It never read files, ran no tools, and produced identical
"GOOD" ratings for all inputs. This made it useless as a quality gate: the `task_cycle`
ship/pivot decision depends on real grade signal.

The requirement: grade Python code with enough signal to make a meaningful ship-or-pivot
decision, using tools already present in the project environment.

## Decision

Replace the stub with a real subprocess-based grader (`_grade_code(path: str) -> GradeResult`)
that runs four tools:

1. **ruff check** — `ruff check {path} --output-format=json` — lint violations
2. **pytest** — `python -m pytest tests/test_{module}.py -q --tb=short` — test failures
3. **mypy** — `python -m mypy {path} --ignore-missing-imports --no-error-summary` — type errors
4. **bandit** — `bandit -r {path} -f json -q` — security findings

**Scoring (deductions from 100):**

| Finding | Deduction |
|---------|-----------|
| Each ruff violation | −3 pts |
| Test suite fails (flat) | −20 pts |
| Each mypy error | −5 pts (capped at −30) |
| bandit HIGH | −15 pts |
| bandit MEDIUM | −5 pts |

**Why these weights:** Tests failing is a hard blocker (−20 flat). Security findings are
weighted heavily (−15 HIGH) because they indicate systemic risk, not just style. Mypy is
capped at −30 because legacy codebases with missing stubs can produce dozens of mypy errors
that don't reflect real bugs; uncapped, mypy alone would bottom-score any large file.

**Test file discovery:** Infers `tests/test_{module}.py` by walking up from the source file
to find a `tests/` directory. If no test file exists, pytest is skipped.

## Consequences

**Positive:**

- Grade reflects actual code quality, not a template
- Four independent quality axes: lint, tests, types, security
- `GradeResult` dataclass is independently testable without subprocesses (mock `_grade_code`)
- Real subprocess runs catch issues that stub analysis missed (e.g., actual import errors)

**Negative / Trade-offs:**

- Running four subprocesses adds latency (~2–5 seconds for small files)
- mypy cap means a file with 10+ mypy errors gets same deduction as one with 6 — known limitation
- Test discovery assumes `tests/test_{module}.py` naming — non-standard layouts skip pytest
- bandit `-r` flag also recurse into imports; for small isolated files this is usually fine
- ruff JSON output format may change between ruff versions — tested against ruff 0.4.x

## Alternatives Considered

- **Inline AST analysis** — parse the file in-process with `ast` module. Rejected: reimplements what ruff/mypy already do; high maintenance burden.
- **pylint** — older, more comprehensive linter. Rejected: ruff is ~10-100x faster and covers 90% of the same rules; pylint adds install dependency complexity.
- **Single tool only** — just ruff. Rejected: ruff catches style/import issues but misses type errors and security vulnerabilities; the composite score is more meaningful.

---

*Recorded 2026-04-05 — Agent Mahoo agentic task cycle implementation*
