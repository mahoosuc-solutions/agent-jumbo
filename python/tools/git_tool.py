"""
Git Tool — agent-callable Git write operations with safety guards.

Wraps GitPython (already used in python/helpers/git.py) to give agents
structured access to git operations without allowing dangerous mutations.

Safety guards (enforced unconditionally):
  - add(): rejects files matching secret/credential patterns (.env, *.pem, etc.)
  - commit(): rejects empty or too-short commit messages (< 10 chars)
  - push(): requires explicit confirmed=true argument; never auto-called by TaskCycle
  - All operations are scoped to the repo root returned by get_git_info()

Actions:
    status   — structured dict of staged/unstaged/untracked files
    diff     — show diff (staged=true for --cached)
    add      — stage files by path (safety-checked)
    commit   — create commit with message
    push     — push to remote (requires confirmed=true)
    branch   — list branches or create a new one
    log      — recent commits as list of dicts
"""

from __future__ import annotations

import fnmatch
import logging
from typing import Any

from git import GitCommandError, InvalidGitRepositoryError, Repo

from python.helpers.tool import Response, Tool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Secret-file patterns that must never be staged
# ---------------------------------------------------------------------------

_SECRET_PATTERNS = [
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.crt",
    "*secret*",
    "*credential*",
    "*password*",
    "id_rsa",
    "id_ed25519",
    ".netrc",
    "*.token",
]

_MIN_COMMIT_MESSAGE_LEN = 10


def _is_secret_file(path: str) -> bool:
    """Return True if *any component* of path matches a secret-file pattern.

    Checks all path components (not just the basename) so that files inside
    directories named 'credentials/' or 'secrets/' are also caught.
    """
    parts = path.replace("\\", "/").split("/")
    return any(fnmatch.fnmatch(part.lower(), pattern.lower()) for part in parts for pattern in _SECRET_PATTERNS)


def _open_repo(repo_path: str) -> Repo:
    return Repo(repo_path, search_parent_directories=True)


def _repo_path() -> str:
    """Return the git repository root path."""
    from python.helpers.git import get_git_info

    return get_git_info()["repo_path"]


# ---------------------------------------------------------------------------
# Core git operations (standalone functions for testability)
# ---------------------------------------------------------------------------


def git_status(repo: Repo) -> dict[str, Any]:
    """Return structured status dict."""
    staged = [d.a_path for d in repo.index.diff("HEAD")] if repo.head.is_valid() else []
    unstaged = [d.a_path for d in repo.index.diff(None)]
    untracked = list(repo.untracked_files)
    return {
        "branch": repo.active_branch.name if not repo.head.is_detached else "detached",
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "is_dirty": repo.is_dirty(untracked_files=True),
        "commit": repo.head.commit.hexsha[:7] if repo.head.is_valid() else None,
    }


def git_diff(repo: Repo, staged: bool = False) -> str:
    """Return diff output."""
    if staged:
        return repo.git.diff("--cached")
    return repo.git.diff()


def git_add(repo: Repo, paths: list[str]) -> dict[str, Any]:
    """Stage files, refusing any that match secret patterns."""
    refused: list[str] = []
    accepted: list[str] = []
    for path in paths:
        if _is_secret_file(path):
            refused.append(path)
        else:
            accepted.append(path)

    if refused:
        logger.warning("git_add: refused secret file(s): %s", refused)
        return {
            "status": "error",
            "error": f"Refused to stage secret files: {refused}. Remove them from the paths list.",
            "refused": refused,
            "staged": [],
        }

    if accepted:
        repo.index.add(accepted)
        logger.info("git_add: staged %d file(s): %s", len(accepted), accepted)

    return {"status": "ok", "staged": accepted}


def git_commit(repo: Repo, message: str) -> dict[str, Any]:
    """Create a commit. Rejects empty or too-short messages."""
    message = message.strip()
    if len(message) < _MIN_COMMIT_MESSAGE_LEN:
        return {
            "status": "error",
            "error": f"Commit message too short (minimum {_MIN_COMMIT_MESSAGE_LEN} chars): {message!r}",
        }

    commit = repo.index.commit(message)
    return {
        "status": "ok",
        "sha": commit.hexsha[:7],
        "message": message,
        "branch": repo.active_branch.name if not repo.head.is_detached else "detached",
    }


def git_push(repo: Repo, remote: str = "origin", branch: str | None = None, confirmed: bool = False) -> dict[str, Any]:
    """Push to remote. Requires confirmed=True — never auto-called by TaskCycle."""
    if not confirmed:
        return {
            "status": "error",
            "error": "Push requires confirmed=true. This is a safety gate: review the grade report before pushing.",
        }

    branch_name = branch or (repo.active_branch.name if not repo.head.is_detached else None)
    if not branch_name:
        return {"status": "error", "error": "Cannot push in detached HEAD state without explicit branch name."}

    try:
        push_info = repo.remote(remote).push(branch_name)
        flags = [str(p.flags) for p in push_info]
        return {"status": "ok", "remote": remote, "branch": branch_name, "push_flags": flags}
    except GitCommandError as exc:
        return {"status": "error", "error": str(exc)}


def git_branch(repo: Repo, name: str | None = None, create: bool = False) -> dict[str, Any]:
    """List branches or create a new one."""
    if name and create:
        try:
            new_branch = repo.create_head(name)
            new_branch.checkout()
            return {"status": "ok", "created": name, "checked_out": True}
        except GitCommandError as exc:
            return {"status": "error", "error": str(exc)}

    branches = [b.name for b in repo.branches]  # type: ignore[attr-defined]
    current = repo.active_branch.name if not repo.head.is_detached else None
    return {"status": "ok", "branches": branches, "current": current}


def git_log(repo: Repo, n: int = 10) -> dict[str, Any]:
    """Return the last *n* commits as a list of dicts."""
    commits = []
    for commit in repo.iter_commits(max_count=n):
        commits.append(
            {
                "sha": commit.hexsha[:7],
                "message": commit.message.strip().split("\n")[0],
                "author": str(commit.author),
                "date": commit.committed_datetime.isoformat(),
            }
        )
    return {"status": "ok", "commits": commits}


# ---------------------------------------------------------------------------
# Tool wrapper
# ---------------------------------------------------------------------------


class GitTool(Tool):
    """Agent-callable Git write operations with safety guards."""

    ALLOWED_ACTIONS = {"status", "diff", "add", "commit", "push", "branch", "log"}

    async def execute(self, **kwargs) -> Response:
        action = self.args.get("action", "status").lower().strip()

        if action not in self.ALLOWED_ACTIONS:
            return Response(
                message=f"Unknown action: {action!r}. Allowed: {', '.join(sorted(self.ALLOWED_ACTIONS))}",
                break_loop=False,
            )

        try:
            repo_root = _repo_path()
            repo = _open_repo(repo_root)
        except (InvalidGitRepositoryError, Exception) as exc:
            return Response(message=f"Failed to open git repository: {exc}", break_loop=False)

        try:
            result = await self._dispatch(action, repo)
        except Exception as exc:
            return Response(message=f"Git operation failed: {exc}", break_loop=False)

        # Format as readable markdown + include structured data in additional
        message = self._format_result(action, result)
        return Response(message=message, break_loop=False, additional=result)

    async def _dispatch(self, action: str, repo: Repo) -> dict[str, Any]:
        if action == "status":
            return git_status(repo)

        if action == "diff":
            staged = self.args.get("staged", "false").lower() == "true"
            diff_output = git_diff(repo, staged=staged)
            return {"status": "ok", "diff": diff_output or "(no changes)"}

        if action == "add":
            raw_paths = self.args.get("paths", "")
            paths = [p.strip() for p in raw_paths.split(",") if p.strip()]
            if not paths:
                return {"status": "error", "error": "No paths provided. Use paths='file1.py,file2.py'"}
            return git_add(repo, paths)

        if action == "commit":
            message = self.args.get("message", "").strip()
            if not message:
                return {"status": "error", "error": "No commit message provided. Use message='...'"}
            return git_commit(repo, message)

        if action == "push":
            remote = self.args.get("remote", "origin")
            branch = self.args.get("branch") or None
            confirmed_raw = self.args.get("confirmed", "false").lower()
            confirmed = confirmed_raw in ("true", "1", "yes")
            return git_push(repo, remote=remote, branch=branch, confirmed=confirmed)

        if action == "branch":
            name = self.args.get("name") or None
            create = self.args.get("create", "false").lower() == "true"
            return git_branch(repo, name=name, create=create)

        if action == "log":
            n = int(self.args.get("n", "10"))
            return git_log(repo, n=n)

        return {"status": "error", "error": f"Unhandled action: {action}"}

    @staticmethod
    def _format_result(action: str, result: dict[str, Any]) -> str:
        if result.get("status") == "error":
            return f"❌ Git {action} failed: {result['error']}"

        if action == "status":
            lines = [f"## Git Status — branch `{result.get('branch', '?')}`", ""]
            if result.get("staged"):
                lines.append(f"**Staged** ({len(result['staged'])} files):")
                for f in result["staged"]:
                    lines.append(f"  - {f}")
                lines.append("")
            if result.get("unstaged"):
                lines.append(f"**Unstaged** ({len(result['unstaged'])} files):")
                for f in result["unstaged"]:
                    lines.append(f"  - {f}")
                lines.append("")
            if result.get("untracked"):
                lines.append(f"**Untracked** ({len(result['untracked'])} files):")
                for f in result["untracked"][:10]:
                    lines.append(f"  - {f}")
                lines.append("")
            if not result.get("is_dirty"):
                lines.append("✓ Working tree clean")
            return "\n".join(lines)

        if action == "diff":
            return f"```diff\n{result.get('diff', '(empty)')}\n```"

        if action == "add":
            staged = result.get("staged", [])
            return f"✓ Staged {len(staged)} file(s): {', '.join(staged)}"

        if action == "commit":
            return f"✓ Committed `{result.get('sha')}` on `{result.get('branch')}`: {result.get('message')}"

        if action == "push":
            return f"✓ Pushed to `{result.get('remote')}/{result.get('branch')}`"

        if action == "branch":
            if "created" in result:
                return f"✓ Created and checked out branch `{result['created']}`"
            current = result.get("current", "?")
            branches = result.get("branches", [])
            return f"Branches ({len(branches)}):\n" + "\n".join(
                f"  {'*' if b == current else ' '} {b}" for b in branches
            )

        if action == "log":
            commits = result.get("commits", [])
            lines = [f"## Recent Commits ({len(commits)})", ""]
            for c in commits:
                lines.append(f"- `{c['sha']}` {c['message']} — {c['author']}")
            return "\n".join(lines)

        return str(result)
