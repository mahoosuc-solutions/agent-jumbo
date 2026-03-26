import os
from datetime import datetime

from git import Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError

from python.helpers import files


def _build_version(branch: str, short_tag: str, commit_hash: str, mode: str) -> str:
    ref = short_tag or commit_hash[:7]
    if branch:
        return branch[0].upper() + " " + (ref or mode)
    return ref or mode


def _archive_git_info(repo_path: str) -> dict:
    branch = os.getenv("AJ_GIT_BRANCH") or os.getenv("BRANCH", "")
    commit_hash = os.getenv("AJ_GIT_COMMIT", "")
    tag = os.getenv("AJ_GIT_TAG", "")
    short_tag = os.getenv("AJ_GIT_SHORT_TAG", "") or tag
    commit_time = os.getenv("AJ_GIT_COMMIT_TIME", "")
    mode = os.getenv("AJ_GIT_MODE", "archive")

    return {
        "branch": branch,
        "commit_hash": commit_hash,
        "commit_time": commit_time,
        "tag": tag,
        "short_tag": short_tag,
        "version": _build_version(branch, short_tag, commit_hash, mode),
        "mode": mode,
        "repo_path": repo_path,
    }


def get_git_info():
    # Get the current working directory (assuming the repo is in the same folder as the script)
    repo_path = files.get_base_dir()

    try:
        # Open the Git repository
        repo = Repo(repo_path, search_parent_directories=True)
    except (InvalidGitRepositoryError, NoSuchPathError):
        return _archive_git_info(repo_path)

    # Ensure the repository is not bare
    if repo.bare:
        raise ValueError(f"Repository at {repo_path} is bare and cannot be used.")

    # Get the current branch name
    branch = repo.active_branch.name if repo.head.is_detached is False else ""

    # Get the latest commit hash
    commit_hash = repo.head.commit.hexsha

    # Get the commit date (ISO 8601 format)
    commit_time = datetime.fromtimestamp(repo.head.commit.committed_date).strftime("%y-%m-%d %H:%M")

    # Get the latest tag description (if available)
    short_tag = ""
    try:
        tag = repo.git.describe(tags=True)
        tag_split = tag.split("-")
        if len(tag_split) >= 3:
            short_tag = "-".join(tag_split[:-1])
        else:
            short_tag = tag
    except Exception:
        tag = ""

    version = _build_version(branch, short_tag, commit_hash, "git")

    # Create the dictionary with collected information
    git_info = {
        "branch": branch,
        "commit_hash": commit_hash,
        "commit_time": commit_time,
        "tag": tag,
        "short_tag": short_tag,
        "version": version,
        "mode": "git",
        "repo_path": repo_path,
    }

    return git_info


def get_version():
    try:
        git_info = get_git_info()
        return str(git_info.get("short_tag", "")).strip() or "unknown"
    except Exception:
        return "unknown"
