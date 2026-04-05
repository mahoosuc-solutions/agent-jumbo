# Code Review Tool

The **code_review** tool runs automated static analysis on Python files or git diffs using four real subprocess tools: ruff (lint), pytest (tests), mypy (type checking), and bandit (security). It produces a 0–100 composite score and a ship/pivot/escalate decision.

Use this tool to evaluate code quality before committing. The TaskCycle tool calls this automatically in `full` mode, but you can also call it directly on any file.

## Available Inputs

Provide exactly one of:

### file

Grade a specific Python file.

- **file** (required): Absolute path to the `.py` file
- **focus** (optional): `"security"`, `"performance"`, `"style"`, or `"all"` (default: `"all"`)

### diff

Grade a git diff string by extracting changed Python files.

- **diff** (required): The diff string (e.g. output of `git diff`)
- **focus** (optional): Same as above

## Scoring System

Starts at 100 and deducts per finding:

| Tool | Finding | Deduction |
|------|---------|-----------|
| ruff | Each lint violation | −3 pts |
| pytest | Test suite fails (flat) | −20 pts |
| mypy | Each type error (cap −30) | −5 pts |
| bandit | HIGH severity finding | −15 pts |
| bandit | MEDIUM severity finding | −5 pts |

**Final score is floored at 0.**

## Decision Thresholds

| Score | Decision | Recommended Action |
|-------|----------|--------------------|
| 90–100 | `ship` | Commit and push |
| 70–89 | `ship_with_warnings` | Commit; address warnings |
| 40–69 | `pivot` | Fix issues before committing |
| 0–39 | `escalate` | Immediate human review |

## When to Use

- Before any `git_tool(action="commit")` call to verify code quality
- After writing or modifying Python code to get objective quality signal
- When the user asks for a code quality assessment
- To decide whether a change is safe to ship or needs revision

## Response Format

Returns a markdown grade report with:

- Score and decision prominently displayed
- Per-tool findings (ruff violations, type errors, security warnings, test output)
- Summary sentence

The `additional` field contains: `{"score": int, "passed": bool, "decision": str}` for programmatic use.

## Examples

### Grade a file

```json
{
    "tool_name": "code_review",
    "tool_args": {
        "file": "/mnt/wdblack/dev/projects/agent-jumbo/python/tools/git_tool.py"
    }
}
```

### Grade a diff

```json
{
    "tool_name": "code_review",
    "tool_args": {
        "diff": "--- a/python/helpers/retry.py\n+++ b/python/helpers/retry.py\n@@ -1 +1 @@\n-import time\n+import time, os"
    }
}
```

### Grade with security focus

```json
{
    "tool_name": "code_review",
    "tool_args": {
        "file": "/mnt/wdblack/dev/projects/agent-jumbo/python/helpers/stripe_provider.py",
        "focus": "security"
    }
}
```
