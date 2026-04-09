# ADR: Git Tool — Agent-Callable Write Operations with Safety Guards

## Status

Accepted

## Context

Agent Mahoo had read-only git access via `python/helpers/git.py` (using GitPython). The
`task_cycle` pipeline's `ship` action requires write operations: staging files, committing,
and eventually pushing to a remote. These operations carry irreversible risk if performed
carelessly:

- Staging `.env` or credential files could leak secrets to remote
- Committing with an empty message creates useless history
- Auto-pushing without human review can publish broken code

A new write-capable git tool is needed with unconditional safety guards — not optional
configurations but hard guards that cannot be disabled by the agent.

## Decision

Implement `GitTool` (`python/tools/git_tool.py`) wrapping GitPython with three
unconditional safety guards:

### Guard 1: Secret file rejection (add action)

`_is_secret_file(path)` uses `fnmatch` pattern matching against 14 patterns:
`.env`, `.env.*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.crt`, `*secret*`,
`*credential*`, `*password*`, `id_rsa`, `id_ed25519`, `.netrc`, `*.token`

If **any** path in the batch matches, **the entire batch is refused** — no partial staging.
This prevents an agent from staging `[".env", "main.py"]` and only having `.env` rejected
while `main.py` goes through (which would still be a valid commit from git's perspective).

### Guard 2: Commit message length (commit action)

Messages shorter than 10 characters after `strip()` are rejected. Whitespace-only messages
(e.g., 10 spaces) collapse to empty after strip and are also rejected.

### Guard 3: Push confirmation gate (push action)

`push` returns an error if `confirmed` is not exactly `"true"`. The `task_cycle` tool
never passes `confirmed=true` automatically — push must always be a separate, explicit
agent action. This means the pipeline is: grade → ship (commit) → (human reviews) → push.

## Consequences

**Positive:**

- Secret leakage through agent-staged files is prevented at the tool level
- Guards apply regardless of which tool calls git_tool (task_cycle, direct agent call, etc.)
- Detached HEAD state is handled explicitly (push fails cleanly with a descriptive error)
- All operations scoped to repo root from `get_git_info()["repo_path"]`

**Negative / Trade-offs:**

- Batch rejection (Guard 1) can frustrate an agent that mixes clean files with one secrets file — the whole add call fails and the agent must re-issue without the secret file
- Pattern matching is basename-only — a file at `config/settings/.env` is caught; a file named `environment_variables.txt` containing secrets is not
- `push` confirmation gate means two tool calls are always required to push (commit + push) — this is intentional but adds one round-trip

## Alternatives Considered

- **gitignore enforcement** — only check against `.gitignore`. Rejected: `.gitignore` might not cover all secret patterns; a new credential file with an unusual name would slip through.
- **Pre-commit hook delegation** — rely on the repo's existing pre-commit hooks. Rejected: hooks run after `git add` completes; we want to refuse before staging.
- **Allowlist approach** — only allow explicitly approved file extensions. Rejected: too restrictive for a general-purpose coding agent that needs to stage diverse file types.

---

*Recorded 2026-04-05 — Agent Mahoo agentic task cycle implementation*
