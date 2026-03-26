import os
import subprocess
from pathlib import Path

from python.helpers import files

# this helper ensures that playwright is installed in /lib/playwright
# should work for both docker and local installation


def get_playwright_binary():
    pw_cache = Path(get_playwright_cache_dir())
    for pattern in (
        "chromium_headless_shell-*/chrome-*/headless_shell",
        "chromium_headless_shell-*/chrome-*/headless_shell.exe",
    ):
        binary = next(pw_cache.glob(pattern), None)
        if binary:
            return binary
    return None


def get_playwright_cache_dir():
    return files.get_abs_path("tmp/playwright")


def ensure_playwright_binary():
    bin = get_playwright_binary()
    if not bin:
        cache = get_playwright_cache_dir()
        env = os.environ.copy()
        env["PLAYWRIGHT_BROWSERS_PATH"] = cache
        try:
            subprocess.check_call(["playwright", "install", "chromium", "--only-shell"], env=env)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                "Playwright browser install failed. If this runtime was built without "
                "Playwright support, rebuild with INSTALL_PLAYWRIGHT=1 or avoid browser-agent features."
            ) from exc
    bin = get_playwright_binary()
    if not bin:
        raise RuntimeError(
            "Playwright binary not found after installation. Rebuild with INSTALL_PLAYWRIGHT=1 "
            "to enable browser-agent and Playwright-based UI automation features."
        )
    return bin
