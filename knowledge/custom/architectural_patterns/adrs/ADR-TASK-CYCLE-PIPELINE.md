# ADR: Task Cycle Pipeline — End-to-End Agentic Orchestration

## Status

Accepted

## Context

Agent Mahoo had mature infrastructure for multi-LLM orchestration (Coordinator, LLMRouter,
TaskDecomposer, ParallelExecutor) but no end-to-end pipeline connecting task intake to
code output to quality evaluation to commit decision. Each step required separate, manual
agent calls with no structured handoff between them.

The need: a single tool that takes a natural-language task description and drives the full
cycle — plan → execute → grade → ship or pivot — without requiring the agent to manually
wire together four separate tools on every task.

## Decision

Implement a `TaskCycle` tool (`python/tools/task_cycle.py`) as an orchestrator that wires:

1. `ComplexityClassifier.score(task)` → complexity tier + model routing
2. `TaskDecomposer.decompose_simple(task)` → list of `SubTask` with DAG dependencies
3. `ParallelExecutor.execute(subtasks, call_fn)` → concurrent LLM dispatch
4. `_grade_code(path)` (from `code_review.py`) → composite 0–100 quality score
5. `_ship_decision(grade)` → `ship | pivot | escalate` decision with next steps

**Actions exposed:** `plan`, `execute`, `grade`, `full`, `ship`

**Key design choices:**

- **`full` is the default action** — safe for everyday use; grades automatically, never pushes
- **`ship` is always a separate, explicit action** — requires `confirmed=true`; never auto-invoked by `full`
- **Grade → decision is deterministic** — score ≥ 90 = ship, 70–89 = ship with warnings, 40–69 = pivot, < 40 = escalate
- **Code extraction from LLM output** — detects Python code blocks in subtask results; grades extracted code in a temp file; does not grade prose output
- **No circular imports** — `task_cycle.py` imports `_grade_code` and `_open_repo`/`_repo_path` at module level so `unittest.mock.patch` can intercept them in tests

## Consequences

**Positive:**

- Single tool call replaces 4-step manual workflow
- Grade-before-commit is automatic, not optional
- Pipeline is testable at each step independently (unit tests for each helper)
- Ship gate prevents accidental commits without quality check

**Negative / Trade-offs:**

- Code extraction is heuristic (detects \`\`\`python blocks) — misses code written to files rather than returned in LLM output
- `full` action grabs only the first LLM-produced code block for grading — multi-file changes are not all graded
- LLM execution in `_run_subtasks` uses the agent's `utility_model`, not the tier-selected model (tier is recorded for planning but execution always uses the agent's configured model due to call_llm API constraints)

## Alternatives Considered

- **Manual chaining** — agent calls coordinator → code_review → git_tool each time. Rejected: too much repeated boilerplate, easy to skip grading.
- **Auto-push on ship score** — auto-push when score ≥ 90. Rejected: push is irreversible and should always be human-approved.
- **Grade via code_execution_tool** — use sandbox to run linters. Rejected: subprocess calls in `code_review.py` already work; adding another indirection adds latency with no benefit.

---

*Recorded 2026-04-05 — Agent Mahoo agentic task cycle implementation*
