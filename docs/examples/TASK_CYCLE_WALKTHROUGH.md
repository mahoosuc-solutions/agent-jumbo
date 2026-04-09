# Task Cycle Walkthrough

A concrete end-to-end example showing how to use `task_cycle`, `code_review`, and `git_tool`
together to take a coding task from description to committed, graded output.

---

## Scenario

You want to add a `retry_with_backoff` utility to the Stripe payment provider.

---

## Step 1 — Plan first, review before executing

Start with `plan` to see how the task will be decomposed and which model will handle it.

```json
{
    "tool_name": "task_cycle",
    "tool_args": {
        "action": "plan",
        "task": "Implement a retry-with-backoff utility for the Stripe payment provider that handles transient network errors"
    }
}
```

**Expected response:**

```
## Task Plan

**Task:** Implement a retry-with-backoff utility for the Stripe payment provider...
**Complexity:** `medium` (confidence 80%)
**Reason:** matched "implement"
**Recommended model:** anthropic/claude-sonnet-4-6
**Estimated subtasks:** 5
**Token budget:** 8,000

### Steps (2)

- **task_0** [generate] → `anthropic/claude-sonnet-4-6`
  > Implement a retry-with-backoff utility...
- **task_1** [synthesize] → `anthropic/claude-sonnet-4-6` (after: task_0)
  > Synthesize the results...
```

Review the plan. If the complexity tier or model looks wrong, you can describe the task
more precisely — adding "simple fix" will push it to EASY tier, "architect entire" to HARD.

---

## Step 2 — Full cycle: execute, grade, decide

Once satisfied with the plan, run the full cycle:

```json
{
    "tool_name": "task_cycle",
    "tool_args": {
        "action": "full",
        "task": "Implement a retry-with-backoff utility for the Stripe payment provider that handles transient network errors"
    }
}
```

**The pipeline runs automatically:**

1. Classifies complexity → MEDIUM → claude-sonnet-4-6
2. Decomposes into subtasks
3. Dispatches to the LLM
4. If the LLM returns code blocks, extracts and grades them
5. Returns a decision

**If the grade is ≥ 70 (ship):**

```
## Task Cycle Complete ✅

**Task:** Implement a retry-with-backoff utility...
**Complexity:** `medium` (confidence 80%)
**Decision:** `SHIP`
**Grade:** 91/100 — Score 91/100 — no issues found

### Subtasks (2)
- `task_0` [anthropic] OK (1240ms)
- `task_1` [anthropic] OK (890ms)

### Next Steps
- Score 91/100 — auto-commit recommended
```

**If the grade is 40–69 (pivot):**

```
## Task Cycle Complete 🔄

**Decision:** `PIVOT`
**Grade:** 58/100 — Score 58/100 — 5 ruff violations, 3 type errors

### Next Steps
- Score 58/100 — revise before committing
- ruff: stripe_retry.py:3 [E401] Multiple imports on one line
- mypy: stripe_retry.py:12: error: Argument 1 has incompatible type...
```

When you get PIVOT, address the specific issues listed, then re-run `full` or `grade`.

---

## Step 3 — Grade a specific file (optional)

If you wrote the code manually (not through task_cycle execute), grade it directly:

```json
{
    "tool_name": "task_cycle",
    "tool_args": {
        "action": "grade",
        "path": "/mnt/wdblack/dev/projects/agent-mahoo/python/helpers/stripe_retry.py"
    }
}
```

This runs the same four-tool grader (ruff + pytest + mypy + bandit) and returns the same
0–100 score and decision. Use this as your quality gate before committing any manually
written Python.

---

## Step 4 — Check git status

Before committing, verify the working tree:

```json
{
    "tool_name": "git_tool",
    "tool_args": {
        "action": "status"
    }
}
```

Review staged vs unstaged vs untracked files. This ensures you commit only what you intend.

---

## Step 5 — Ship: stage and commit

Once the grade is ≥ 70, ship via `task_cycle ship` (which internally calls `git_tool add`
then `git_tool commit`):

```json
{
    "tool_name": "task_cycle",
    "tool_args": {
        "action": "ship",
        "confirmed": "true",
        "message": "feat: add retry-with-backoff utility to Stripe payment provider",
        "paths": "python/helpers/stripe_retry.py,tests/test_stripe_retry.py"
    }
}
```

**Response:**

```
Shipped: committed `a3f9c21` on `feature/stripe-retry`

> feat: add retry-with-backoff utility to Stripe payment provider

Run `git_tool(action='push', confirmed='true')` to push to remote.
```

---

## Step 6 — Push to remote (after human review)

The ship step commits but does **not** push. After reviewing the commit locally:

```json
{
    "tool_name": "git_tool",
    "tool_args": {
        "action": "push",
        "confirmed": "true",
        "remote": "origin"
    }
}
```

`confirmed: "true"` is required — this is the final human-approval gate before code
leaves the local repository.

---

## Pivot → Revise → Re-grade cycle

When `task_cycle full` returns PIVOT:

1. Read the `next_steps` list — each item is a specific issue to fix
2. Fix the issues in the relevant file
3. Re-grade: `task_cycle(action="grade", path="...")`
4. If score ≥ 70: proceed to ship
5. If still PIVOT: repeat

You can also re-run `full` with a more specific task description that guides the LLM
toward cleaner output — adding constraints like "use type annotations", "no unused imports",
"follow ruff E-series rules" in the task string improves first-pass grade scores.

---

## Safety Reminders

| Rule | Why |
|------|-----|
| `ship` requires `confirmed: "true"` | Prevents accidental commits |
| `push` requires `confirmed: "true"` | Push is irreversible without force-push |
| Secret files (`.env`, `*.pem`) are refused at `add` | Prevents credential leaks |
| Commit messages must be ≥ 10 characters | Prevents empty/useless history |
| Grade < 40 → escalate (no auto-commit) | Security or test failures need human review |

---

## Quick Reference

| Goal | Tool call |
|------|-----------|
| Preview decomposition | `task_cycle(action="plan", task="...")` |
| Full pipeline | `task_cycle(action="full", task="...")` |
| Grade a file | `task_cycle(action="grade", path="...")` |
| Commit approved output | `task_cycle(action="ship", confirmed="true", message="...", paths="...")` |
| Push to remote | `git_tool(action="push", confirmed="true")` |
| Check working tree | `git_tool(action="status")` |
| View diff before commit | `git_tool(action="diff", staged="true")` |
| Create feature branch | `git_tool(action="branch", name="feature/...", create="true")` |
