"""E2E test fixtures for Agent Zero.

Provides server management, browser lifecycle, and authentication helpers
for Playwright-based end-to-end tests.
"""

import os
import socket
import subprocess
import sys
import time
import urllib.request

import pytest


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
def server_port() -> int:
    return _find_free_port()


@pytest.fixture(scope="session")
def app_server(server_port: int):
    """Start the Flask app server with auth enabled for the test session."""
    env = os.environ.copy()
    env["WEB_UI_HOST"] = "127.0.0.1"
    env["WEB_UI_PORT"] = str(server_port)
    env["AUTH_LOGIN"] = "testuser"
    env["AUTH_PASSWORD"] = "testpass"  # pragma: allowlist secret
    env["TOKENIZERS_PARALLELISM"] = "false"

    proc = subprocess.Popen(
        [sys.executable, "run_ui.py"],
        env=env,
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    base_url = f"http://127.0.0.1:{server_port}"
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


@pytest.fixture(scope="session")
def browser():
    """Launch a headless Chromium browser for the test session."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright not available")

    pw = sync_playwright().start()
    try:
        brw = pw.chromium.launch(headless=True)
    except Exception:
        pw.stop()
        pytest.skip("Playwright browser not installed (run: playwright install chromium)")

    yield brw

    brw.close()
    pw.stop()


@pytest.fixture()
def page(browser):
    """Create a fresh browser page for each test."""
    pg = browser.new_page()
    yield pg
    pg.close()


@pytest.fixture()
def authenticated_page(page, app_server: str):
    """Log in and yield an authenticated page at the app root."""
    page.goto(f"{app_server}/login", wait_until="domcontentloaded")

    page.fill('input[name="username"], input[type="text"]', "testuser")
    page.fill('input[name="password"], input[type="password"]', "testpass")
    page.click('button[type="submit"]')

    # Wait for redirect away from login page
    page.wait_for_url(lambda url: "/login" not in url, timeout=15000)

    yield page


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Capture a screenshot on test failure for debugging."""
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed:
        pg = item.funcargs.get("page") or item.funcargs.get("authenticated_page")
        if pg:
            screenshots_dir = os.path.join(os.path.dirname(__file__), "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            pg.screenshot(path=os.path.join(screenshots_dir, f"{item.name}.png"))
