"""
Tests for GitTool — agent-callable git operations with safety guards.

Uses unittest.mock to patch GitPython's Repo so no real git operations
run during the test suite. Safety guard assertions are the critical tests.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from python.tools.git_tool import (
    GitTool,
    _is_secret_file,
    git_add,
    git_branch,
    git_commit,
    git_diff,
    git_log,
    git_push,
    git_status,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_repo(branch="main", dirty=False, staged=None, unstaged=None, untracked=None):
    """Build a minimal GitPython Repo mock."""
    repo = MagicMock()

    # Branch
    repo.active_branch.name = branch
    repo.head.is_detached = False
    repo.head.is_valid.return_value = True
    repo.head.commit.hexsha = "abc1234567890"  # pragma: allowlist secret

    # Index diffs
    def _diff_item(path):
        m = MagicMock()
        m.a_path = path
        return m

    staged_paths = staged or []
    unstaged_paths = unstaged or []
    repo.index.diff.side_effect = lambda ref: [
        _diff_item(p) for p in (staged_paths if ref == "HEAD" else unstaged_paths)
    ]
    repo.untracked_files = untracked or []
    repo.is_dirty.return_value = dirty

    # Branches list
    b = MagicMock()
    b.name = branch
    repo.branches = [b]

    return repo


def _make_tool(args: dict, agent=None) -> GitTool:
    """Construct a GitTool without a real Agent."""
    tool = GitTool.__new__(GitTool)
    tool.args = args
    tool.agent = agent or MagicMock()
    tool.name = "git_tool"
    tool.method = None
    tool.message = ""
    tool.loop_data = None
    return tool


# ---------------------------------------------------------------------------
# _is_secret_file
# ---------------------------------------------------------------------------


class TestIsSecretFile:
    @pytest.mark.parametrize(
        "path",
        [
            ".env",
            ".env.local",
            ".env.production",
            "server.pem",
            "private.key",
            "my_secret_token.txt",
            "credentials.json",
            "id_rsa",
            "id_ed25519",
            "app.p12",
            "cert.pfx",
            "service.crt",
            "api.token",
        ],
    )
    def test_secret_files_are_detected(self, path):
        assert _is_secret_file(path), f"Expected {path!r} to be identified as a secret file"

    @pytest.mark.parametrize(
        "path",
        [
            "main.py",
            "config.py",
            "requirements.txt",
            "README.md",
            "tests/test_auth.py",
            "src/utils/helpers.py",
        ],
    )
    def test_normal_files_are_allowed(self, path):
        assert not _is_secret_file(path), f"Expected {path!r} NOT to be a secret file"


# ---------------------------------------------------------------------------
# git_status
# ---------------------------------------------------------------------------


class TestGitStatus:
    def test_returns_branch_name(self):
        repo = _make_mock_repo(branch="feature/new-thing")
        result = git_status(repo)
        assert result["branch"] == "feature/new-thing"

    def test_returns_staged_files(self):
        repo = _make_mock_repo(staged=["src/foo.py", "src/bar.py"])
        result = git_status(repo)
        assert "src/foo.py" in result["staged"]

    def test_returns_untracked_files(self):
        repo = _make_mock_repo(untracked=["new_file.py"])
        result = git_status(repo)
        assert "new_file.py" in result["untracked"]

    def test_is_dirty_when_files_changed(self):
        repo = _make_mock_repo(dirty=True)
        result = git_status(repo)
        assert result["is_dirty"] is True


# ---------------------------------------------------------------------------
# git_diff
# ---------------------------------------------------------------------------


class TestGitDiff:
    def test_diff_calls_git_diff(self):
        repo = MagicMock()
        repo.git.diff.return_value = "--- a/foo.py\n+++ b/foo.py\n@@ -1 +1 @@\n-x\n+y"
        result = git_diff(repo, staged=False)
        assert "-x" in result
        repo.git.diff.assert_called_once_with()

    def test_staged_diff_uses_cached_flag(self):
        repo = MagicMock()
        repo.git.diff.return_value = ""
        git_diff(repo, staged=True)
        repo.git.diff.assert_called_once_with("--cached")


# ---------------------------------------------------------------------------
# git_add — safety guards
# ---------------------------------------------------------------------------


class TestGitAdd:
    def test_stages_normal_files(self):
        repo = _make_mock_repo()
        result = git_add(repo, ["src/main.py", "tests/test_main.py"])
        assert result["status"] == "ok"
        assert "src/main.py" in result["staged"]
        repo.index.add.assert_called_once()

    def test_refuses_env_file(self):
        repo = _make_mock_repo()
        result = git_add(repo, [".env"])
        assert result["status"] == "error"
        assert ".env" in result["refused"]
        repo.index.add.assert_not_called()

    def test_refuses_pem_file(self):
        repo = _make_mock_repo()
        result = git_add(repo, ["private.pem"])
        assert result["status"] == "error"
        assert "private.pem" in result["refused"]

    def test_refuses_mixed_list_with_secret(self):
        repo = _make_mock_repo()
        result = git_add(repo, ["clean.py", ".env.production"])
        assert result["status"] == "error"
        # When any secret is present, the whole batch is refused
        assert ".env.production" in result["refused"]

    def test_empty_paths_returns_error(self):
        repo = _make_mock_repo()
        # git_add with empty list stages nothing but doesn't error
        result = git_add(repo, [])
        assert result["status"] == "ok"
        assert result["staged"] == []


# ---------------------------------------------------------------------------
# git_commit — message guards
# ---------------------------------------------------------------------------


class TestGitCommit:
    def test_commits_with_valid_message(self):
        repo = _make_mock_repo()
        fake_commit = MagicMock()
        fake_commit.hexsha = "deadbeef1234"  # pragma: allowlist secret
        repo.index.commit.return_value = fake_commit

        result = git_commit(repo, "feat: add payment router tests")
        assert result["status"] == "ok"
        assert result["sha"] == "deadbee"  # hexsha[:7]

    def test_rejects_empty_message(self):
        repo = _make_mock_repo()
        result = git_commit(repo, "")
        assert result["status"] == "error"
        assert "too short" in result["error"].lower()
        repo.index.commit.assert_not_called()

    def test_rejects_short_message(self):
        repo = _make_mock_repo()
        result = git_commit(repo, "fix bug")  # 7 chars < 10 minimum
        assert result["status"] == "error"
        repo.index.commit.assert_not_called()

    def test_exactly_min_length_is_accepted(self):
        repo = _make_mock_repo()
        fake_commit = MagicMock()
        fake_commit.hexsha = "abc1234567"  # pragma: allowlist secret
        repo.index.commit.return_value = fake_commit

        message = "x" * 10  # exactly 10 chars
        result = git_commit(repo, message)
        assert result["status"] == "ok"

    def test_whitespace_only_message_rejected(self):
        repo = _make_mock_repo()
        result = git_commit(repo, "          ")  # 10 spaces, stripped = empty
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# git_push — confirmation gate
# ---------------------------------------------------------------------------


class TestGitPush:
    def test_push_without_confirmed_returns_error(self):
        repo = _make_mock_repo()
        result = git_push(repo, confirmed=False)
        assert result["status"] == "error"
        assert "confirmed" in result["error"].lower()
        repo.remote.assert_not_called()

    def test_push_with_confirmed_true_calls_remote(self):
        repo = _make_mock_repo(branch="main")
        mock_push_info = MagicMock()
        mock_push_info.flags = 0
        repo.remote.return_value.push.return_value = [mock_push_info]

        result = git_push(repo, remote="origin", confirmed=True)
        assert result["status"] == "ok"
        repo.remote.assert_called_once_with("origin")

    def test_push_in_detached_head_requires_branch(self):
        repo = MagicMock()
        repo.head.is_detached = True
        result = git_push(repo, confirmed=True, branch=None)
        assert result["status"] == "error"
        assert "detached" in result["error"].lower()

    def test_push_git_error_returns_error_dict(self):
        from git import GitCommandError

        repo = _make_mock_repo(branch="main")
        repo.remote.return_value.push.side_effect = GitCommandError("push", 128)

        result = git_push(repo, confirmed=True)
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# git_branch
# ---------------------------------------------------------------------------


class TestGitBranch:
    def test_list_branches(self):
        repo = _make_mock_repo(branch="main")
        result = git_branch(repo)
        assert result["status"] == "ok"
        assert "main" in result["branches"]
        assert result["current"] == "main"

    def test_create_branch(self):
        repo = MagicMock()
        repo.head.is_detached = False
        repo.active_branch.name = "main"
        new_head = MagicMock()
        repo.create_head.return_value = new_head
        repo.branches = []

        result = git_branch(repo, name="feature/new-tool", create=True)
        assert result["status"] == "ok"
        assert result["created"] == "feature/new-tool"
        new_head.checkout.assert_called_once()


# ---------------------------------------------------------------------------
# git_log
# ---------------------------------------------------------------------------


class TestGitLog:
    def test_returns_commit_list(self):
        repo = MagicMock()
        commit = MagicMock()
        commit.hexsha = "abc1234567"  # pragma: allowlist secret
        commit.message = "feat: add new tool\n"
        commit.author.__str__.return_value = "Alice"
        from datetime import datetime, timezone

        commit.committed_datetime = datetime(2026, 4, 5, tzinfo=timezone.utc)
        repo.iter_commits.return_value = [commit]

        result = git_log(repo, n=5)
        assert result["status"] == "ok"
        assert len(result["commits"]) == 1
        assert result["commits"][0]["sha"] == "abc1234"
        assert "feat: add new tool" in result["commits"][0]["message"]


# ---------------------------------------------------------------------------
# GitTool.execute() — action dispatch via mocked _repo_path + Repo
# ---------------------------------------------------------------------------


class TestGitToolExecute:
    @pytest.mark.asyncio
    async def test_unknown_action_returns_error(self):
        tool = _make_tool({"action": "teleport"})
        response = await tool.execute()
        assert "Unknown action" in response.message
        assert response.break_loop is False

    @pytest.mark.asyncio
    async def test_status_action_returns_markdown(self):
        tool = _make_tool({"action": "status"})
        mock_repo = _make_mock_repo(branch="main")

        with patch("python.tools.git_tool._repo_path", return_value="/fake/repo"):
            with patch("python.tools.git_tool._open_repo", return_value=mock_repo):
                response = await tool.execute()

        assert "Git Status" in response.message
        assert response.break_loop is False
        assert response.additional is not None

    @pytest.mark.asyncio
    async def test_add_safety_guard_via_tool(self):
        tool = _make_tool({"action": "add", "paths": ".env"})
        mock_repo = _make_mock_repo()

        with patch("python.tools.git_tool._repo_path", return_value="/fake/repo"):
            with patch("python.tools.git_tool._open_repo", return_value=mock_repo):
                response = await tool.execute()

        assert "error" in response.message.lower() or "refused" in response.message.lower()

    @pytest.mark.asyncio
    async def test_push_without_confirmed_via_tool(self):
        tool = _make_tool({"action": "push"})
        mock_repo = _make_mock_repo()

        with patch("python.tools.git_tool._repo_path", return_value="/fake/repo"):
            with patch("python.tools.git_tool._open_repo", return_value=mock_repo):
                response = await tool.execute()

        assert "confirmed" in response.message.lower()

    @pytest.mark.asyncio
    async def test_commit_short_message_via_tool(self):
        tool = _make_tool({"action": "commit", "message": "fix"})
        mock_repo = _make_mock_repo()

        with patch("python.tools.git_tool._repo_path", return_value="/fake/repo"):
            with patch("python.tools.git_tool._open_repo", return_value=mock_repo):
                response = await tool.execute()

        assert "too short" in response.message.lower() or "failed" in response.message.lower()
