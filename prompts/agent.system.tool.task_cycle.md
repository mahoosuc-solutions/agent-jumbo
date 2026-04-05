# Task Cycle Tool

The **task_cycle** tool is the end-to-end agentic pipeline for Agent Jumbo: it takes a task description, classifies its complexity, decomposes it into subtasks with optimal model assignments, dispatches execution, grades code output with real linters and tests, and returns a ship/pivot/escalate decision.

Use this tool when you receive a coding or analysis task that you want to plan, execute, evaluate, and potentially commit — rather than doing each step manually.

## Available Actions

### plan

Decompose a task into steps with complexity tier and model assignments. Does NOT execute.

- **task** (required): The task description
- Returns: list of steps with provider/model assignments, complexity tier, token budget

### execute

Decompose AND dispatch subtasks via the configured LLM. Does NOT grade or commit.

- **task** (required): The task description
- Returns: execution results per subtask with latency and output previews

### grade

Run static analysis (ruff, pytest, mypy, bandit) on an existing file and return a 0–100 score.

- **path** (required): Absolute path to the Python file to grade
- Returns: grade report with score, decision (ship/pivot/escalate), and per-tool findings

### full *(default)*

Complete pipeline: classify → decompose → execute → grade (if code produced) → ship decision.

- **task** (required): The task description
- Returns: structured decision dict with grade, next_steps, and execution summary

### ship

Commit approved output to git after human review. Requires explicit confirmation.

- **confirmed** (required): Must be `"true"` — safety gate; never inferred
- **message** (required): Commit message (minimum 10 characters)
- **paths** (required): Comma-separated file paths to stage and commit
- Returns: commit SHA and branch; instructs user to push separately via git_tool

## Decision Thresholds

| Score | Decision | Meaning |
|-------|----------|---------|
| 90–100 | `ship` | Auto-commit recommended |
| 70–89 | `ship` | Commit with warnings noted |
| 40–69 | `pivot` | Revise — issues list returned |
| 0–39 | `escalate` | Critical issues — human review required |

## Complexity Tiers

The classifier automatically routes to the right model:

| Tier | Keywords | Model |
|------|---------|-------|
| SIMPLE | list, show, what is, read | ollama/llama3.2 |
| EASY | fix, add, update, rename | gemini-2.0-flash |
| MEDIUM | implement, refactor, integrate | claude-sonnet-4-6 |
| HARD | architect, rewrite, migrate entire | claude-opus-4-6 |

## When to Use

- Use `plan` first when you want to show the user how a task would be broken down before committing
- Use `full` for self-contained coding tasks where you want automatic grading
- Use `grade` after writing code manually to get a quality score before committing
- Use `ship` only after reviewing the grade report — never call it automatically

## Safety Rules

- `ship` is **always gated** — it will reject if `confirmed` is not exactly `"true"`
- `ship` calls `git_tool` internally; it stages and commits but does NOT push
- After shipping, call `git_tool(action="push", confirmed="true")` only after explicit human approval
- The grader runs real subprocesses (ruff, pytest, mypy, bandit) — results reflect actual code quality

## Examples

### Plan a task first

```json
{
    "tool_name": "task_cycle",
    "tool_args": {
        "action": "plan",
        "task": "Add a rate-limiting middleware to the FastAPI payment endpoints"
    }
}
```

### Full cycle — plan, execute, grade, decide

```json
{
    "tool_name": "task_cycle",
    "tool_args": {
        "action": "full",
        "task": "Implement a retry-with-backoff utility for the Stripe payment provider"
    }
}
```

### Grade an existing file

```json
{
    "tool_name": "task_cycle",
    "tool_args": {
        "action": "grade",
        "path": "/mnt/wdblack/dev/projects/agent-jumbo/python/tools/git_tool.py"
    }
}
```

### Ship after human approves grade report

```json
{
    "tool_name": "task_cycle",
    "tool_args": {
        "action": "ship",
        "confirmed": "true",
        "message": "feat: add retry-with-backoff to Stripe provider",
        "paths": "python/helpers/stripe_retry.py,tests/test_stripe_retry.py"
    }
}
```
