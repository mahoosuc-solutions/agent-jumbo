"""
Async Playwright fixture infrastructure.

Provides async-compatible browser and page fixtures that work alongside
the existing sync tests. New UI tests should use these fixtures for
better compatibility with pytest-asyncio's auto mode.

Usage in new async test files::

    import pytest
    from playwright.async_api import Page

    @pytest.mark.asyncio
    async def test_homepage(async_page: Page, ui_server: str):
        await async_page.goto(ui_server)
        assert await async_page.title()
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request

import pytest
import pytest_asyncio


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_server(url: str, timeout: float = 90.0) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(0.5)
    raise TimeoutError(f"Server did not become ready at {url}")


@pytest.fixture(scope="session")
def ui_server():
    """Start the web UI server for async Playwright tests."""
    port = _find_free_port()
    env = os.environ.copy()
    env["WEB_UI_HOST"] = "127.0.0.1"
    env["WEB_UI_PORT"] = str(port)
    env["AUTH_LOGIN"] = ""
    env["AUTH_PASSWORD"] = ""
    env["TOKENIZERS_PARALLELISM"] = "false"

    proc = subprocess.Popen(
        [sys.executable, "run_ui.py"],
        env=env,
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_for_server(base_url, timeout=90)
    except TimeoutError:
        proc.kill()
        raise

    yield base_url

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest_asyncio.fixture(scope="session")
async def async_browser():
    """Async Playwright browser fixture (session-scoped)."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        pytest.skip("Playwright not available")

    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.launch(headless=True)
    except Exception:
        await pw.stop()
        pytest.skip("Playwright browser not installed (run: playwright install chromium)")

    yield browser

    await browser.close()
    await pw.stop()


@pytest_asyncio.fixture
async def async_page(async_browser):
    """Async Playwright page fixture (per-test)."""
    page = await async_browser.new_page()
    yield page
    await page.close()
