# Git Tool

The **git_tool** provides agent-callable git write operations with unconditional safety guards. It wraps GitPython to give structured access to git operations without allowing dangerous mutations.

**Safety guards are enforced on every call and cannot be bypassed.**

## Available Actions

### status

Show current branch, staged files, unstaged changes, and untracked files.

- No arguments required
- Returns: structured dict + markdown summary

### diff

Show the working-directory diff or staged diff.

- **staged** (optional): `"true"` for `--cached` (staged diff), default `"false"`
- Returns: diff output as a code block

### add

Stage files for commit. Refuses any file matching secret patterns.

- **paths** (required): Comma-separated file paths to stage
- Returns: list of staged files, or error with refused paths

### commit

Create a commit with the given message.

- **message** (required): Commit message (minimum 10 characters, non-whitespace)
- Returns: commit SHA and branch name

### push

Push the current branch to a remote. **Always requires explicit confirmation.**

- **confirmed** (required): Must be exactly `"true"` — safety gate
- **remote** (optional): Remote name, default `"origin"`
- **branch** (optional): Branch name; defaults to current branch
- Returns: push result or error if detached HEAD without explicit branch

### branch

List all branches or create a new one.

- **name** (optional): Branch name (required if creating)
- **create** (optional): `"true"` to create and checkout the branch
- Returns: branch list with current branch marked, or new branch confirmation

### log

Show recent commit history.

- **n** (optional): Number of commits to show (default: 10)
- Returns: list of commits with SHA, message, author, date

## Safety Guards (Non-Negotiable)

**Secret file rejection (add action):** The following patterns are unconditionally refused:
`.env`, `.env.*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.crt`, `*secret*`, `*credential*`, `*password*`, `id_rsa`, `id_ed25519`, `.netrc`, `*.token`

**Commit message guard:** Messages shorter than 10 characters (after stripping whitespace) are rejected.

**Push gate:** `push` always returns an error if `confirmed` is not `"true"`. The TaskCycle tool never calls push automatically — it must always be a separate, explicit agent action after human review.

## When to Use

- Use `status` before starting any git workflow to understand current state
- Use `diff` to review what would be committed
- Use `add` + `commit` to record completed work (after grading with task_cycle or code_review)
- Use `push` only after the user has seen the commit and grade report
- Use `branch` to create feature branches before starting new work
- Use `log` to understand recent history before making architectural decisions

## Examples

### Check status before committing

```json
{
    "tool_name": "git_tool",
    "tool_args": {
        "action": "status"
    }
}
```

### Stage and commit specific files

```json
{
    "tool_name": "git_tool",
    "tool_args": {
        "action": "add",
        "paths": "python/tools/new_feature.py,tests/test_new_feature.py"
    }
}
```

```json
{
    "tool_name": "git_tool",
    "tool_args": {
        "action": "commit",
        "message": "feat: add retry-with-backoff to payment provider"
    }
}
```

### Push after explicit human approval

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

### Create a feature branch

```json
{
    "tool_name": "git_tool",
    "tool_args": {
        "action": "branch",
        "name": "feature/payment-retry",
        "create": "true"
    }
}
```
