from git.exc import InvalidGitRepositoryError

from python.helpers import git


def test_get_git_info_falls_back_to_archive_metadata(monkeypatch):
    monkeypatch.setenv("BRANCH", "main")
    monkeypatch.setenv(
        "AJ_GIT_COMMIT",
        "539e08e90b3fa96786cf9e0b52cb4a5f7ab5a6ca",  # pragma: allowlist secret
    )
    monkeypatch.setenv("AJ_GIT_TAG", "v1.2.3")
    monkeypatch.setenv("AJ_GIT_COMMIT_TIME", "26-03-26 03:45")
    monkeypatch.setattr(
        git, "Repo", lambda *_args, **_kwargs: (_ for _ in ()).throw(InvalidGitRepositoryError("archive"))
    )

    info = git.get_git_info()

    assert info["mode"] == "archive"
    assert info["branch"] == "main"
    assert info["commit_hash"] == "539e08e90b3fa96786cf9e0b52cb4a5f7ab5a6ca"  # pragma: allowlist secret
    assert info["tag"] == "v1.2.3"
    assert info["version"] == "M v1.2.3"


def test_get_git_info_marks_live_git_mode():
    info = git.get_git_info()

    assert info["mode"] in {"git", "archive"}
    assert "version" in info
