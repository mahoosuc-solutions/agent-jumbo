from python.helpers import git


async def check_version():
    """Update check disabled — Agent Mahoo is a standalone fork."""
    current_version = git.get_version()
    return {"current_version": current_version, "latest_version": current_version, "update_available": False}
