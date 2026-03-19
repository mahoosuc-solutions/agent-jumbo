"""E2E tests for the work queue dashboard API and browser UI."""

import json
import time
import urllib.error
import urllib.request

import pytest

pytestmark = [pytest.mark.e2e]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cookie_header(auth_cookies: dict) -> str:
    return "; ".join(f"{k}={v}" for k, v in auth_cookies.items())


def _get_csrf_token(base_url: str, auth_cookies: dict, retries: int = 5) -> str:
    """Fetch a CSRF token from /csrf_token, retrying on 429."""
    status = None
    for attempt in range(retries):
        req = urllib.request.Request(
            f"{base_url}/csrf_token",
            method="GET",
        )
        req.add_header("Cookie", _cookie_header(auth_cookies))
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            assert data.get("ok"), f"CSRF endpoint returned ok=false: {data}"
            return data["token"]
        except urllib.error.HTTPError as e:
            status = e.code
            if e.code == 429 and attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise
    pytest.fail(f"CSRF token fetch failed after {retries} retries (last status: {status})")


def _api_post(app_server: str, auth_cookies: dict, endpoint: str, body: dict) -> dict:
    """
    POST JSON to /api/backend/<endpoint> with CSRF token and auth cookies.
    Returns the parsed JSON response dict.
    Raises urllib.error.HTTPError on non-2xx responses (caller can inspect .code).
    """
    csrf = _get_csrf_token(app_server, auth_cookies)
    payload = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{app_server}/api/backend/{endpoint}",
        data=payload,
        method="POST",
    )
    req.add_header("Cookie", _cookie_header(auth_cookies))
    req.add_header("Content-Type", "application/json")
    req.add_header("X-CSRF-Token", csrf)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        # Re-raise with the body attached so callers can inspect error JSON
        exc._response_body = exc.read().decode(errors="replace")
        raise


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_dashboard_api_returns_stats(app_server, auth_cookies):
    """POST work_queue_dashboard {action: dashboard} returns success, total, by_status."""
    data = _api_post(app_server, auth_cookies, "work_queue_dashboard", {"action": "dashboard"})
    assert data.get("success"), f"Expected success=True, got: {data}"
    assert "total" in data, f"Expected 'total' key in response: {data}"
    assert "by_status" in data, f"Expected 'by_status' key in response: {data}"
    assert isinstance(data["by_status"], dict), f"Expected by_status to be a dict: {data}"


@pytest.mark.e2e
def test_list_items_api_with_pagination(app_server, auth_cookies):
    """POST work_queue_dashboard {action: list} returns items array and total."""
    data = _api_post(
        app_server,
        auth_cookies,
        "work_queue_dashboard",
        {"action": "list", "page": 1, "page_size": 10},
    )
    assert data.get("success"), f"Expected success=True, got: {data}"
    assert "items" in data, f"Expected 'items' key in response: {data}"
    assert isinstance(data["items"], list), f"Expected items to be a list: {data}"
    assert "total" in data, f"Expected 'total' key in response: {data}"


@pytest.mark.e2e
def test_list_items_api_with_status_filter(app_server, auth_cookies):
    """POST work_queue_dashboard list with status filter returns valid response."""
    data = _api_post(
        app_server,
        auth_cookies,
        "work_queue_dashboard",
        {"action": "list", "page": 1, "page_size": 25, "status": "discovered"},
    )
    assert data.get("success"), f"Expected success=True, got: {data}"
    assert "items" in data, f"Expected 'items' key in response: {data}"
    # Every returned item (if any) should match the requested status
    for item in data["items"]:
        assert item.get("status") == "discovered", (
            f"Item status mismatch — expected 'discovered', got: {item.get('status')}"
        )


@pytest.mark.e2e
def test_projects_api_list(app_server, auth_cookies):
    """POST work_queue_projects {action: list} returns a valid response."""
    data = _api_post(app_server, auth_cookies, "work_queue_projects", {"action": "list"})
    assert data.get("success"), f"Expected success=True, got: {data}"
    # Response must have either a 'projects' list key or indicate empty
    assert "projects" in data or "items" in data, f"Expected 'projects' or 'items' key in response: {data}"


@pytest.mark.e2e
def test_scan_api_requires_project(app_server, auth_cookies):
    """POST work_queue_scan without project_path returns an error response."""
    try:
        data = _api_post(app_server, auth_cookies, "work_queue_scan", {"action": "scan_codebase"})
        # If server returns 200, it should set success=False or carry an error message
        assert not data.get("success") or "error" in data, (
            f"Expected error response when project_path missing, got: {data}"
        )
    except urllib.error.HTTPError as exc:
        # A 4xx / 5xx response is also an acceptable error signal
        assert exc.code in (400, 422, 500), (
            f"Expected 400/422/500 for missing project_path, got {exc.code}: {getattr(exc, '_response_body', '')}"
        )


@pytest.mark.e2e
def test_settings_api_get(app_server, auth_cookies):
    """POST work_queue_settings {action: get} returns success and settings dict."""
    data = _api_post(app_server, auth_cookies, "work_queue_settings", {"action": "get"})
    assert data.get("success"), f"Expected success=True, got: {data}"
    assert "settings" in data, f"Expected 'settings' key in response: {data}"
    assert isinstance(data["settings"], dict), f"Expected settings to be a dict: {data}"


@pytest.mark.e2e
def test_schedule_api_get(app_server, auth_cookies):
    """POST work_queue_settings {action: get_schedule} returns schedule shape."""
    data = _api_post(app_server, auth_cookies, "work_queue_settings", {"action": "get_schedule"})
    assert data.get("success"), f"Expected success=True, got: {data}"
    # The schedule object must contain enabled, cron, and scan_types keys
    schedule = data.get("schedule", data)  # some endpoints inline the schedule
    assert "enabled" in schedule or "enabled" in data, f"Expected 'enabled' key in schedule response: {data}"
    assert "cron" in schedule or "cron" in data, f"Expected 'cron' key in schedule response: {data}"
    assert "scan_types" in schedule or "scan_types" in data, f"Expected 'scan_types' key in schedule response: {data}"


@pytest.mark.e2e
def test_item_get_not_found(app_server, auth_cookies):
    """POST work_queue_item_get with a nonexistent ID returns an error response."""
    NONEXISTENT_ID = 999_999_999
    try:
        data = _api_post(app_server, auth_cookies, "work_queue_item_get", {"item_id": NONEXISTENT_ID})
        # If 200, success must be False or an error key must be present
        assert not data.get("success") or "error" in data, f"Expected error for nonexistent item ID, got: {data}"
    except urllib.error.HTTPError as exc:
        assert exc.code in (400, 404, 422, 500), (
            f"Expected 4xx/500 for nonexistent item, got {exc.code}: {getattr(exc, '_response_body', '')}"
        )


# ---------------------------------------------------------------------------
# Browser-level tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_work_queue_page_loads(authenticated_page, app_server):
    """Navigate to /work-queue and verify the page renders meaningful content."""
    page = authenticated_page
    page.goto(f"{app_server}/work-queue", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    body_text = page.inner_text("body")
    # The page must contain "Work Queue" text (heading or breadcrumb)
    assert "Work Queue" in body_text or "work queue" in body_text.lower(), (
        f"Expected 'Work Queue' heading on page, got body text: {body_text[:300]}"
    )


@pytest.mark.e2e
def test_work_queue_shows_stats_cards(authenticated_page, app_server):
    """Work queue dashboard should display stat cards (Total, Discovered, etc.)."""
    page = authenticated_page
    page.goto(f"{app_server}/work-queue", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)

    body_text = page.inner_text("body")
    body_lower = body_text.lower()

    # At least one of the known stat card labels should appear
    stat_labels = ["total", "discovered", "queued", "in progress", "done"]
    found = [label for label in stat_labels if label in body_lower]
    assert found, (
        f"Expected at least one stat card label ({stat_labels}) on work queue page. "
        f"Body text (first 500 chars): {body_text[:500]}"
    )


@pytest.mark.e2e
def test_work_queue_filter_dropdown_present(authenticated_page, app_server):
    """Work queue page should have at least one filter <select> element."""
    page = authenticated_page
    page.goto(f"{app_server}/work-queue", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    # Look for select elements (status filter, sort filter, etc.)
    selects = page.query_selector_all("select")
    if not selects:
        # Fallback: some UIs use role="combobox" or custom dropdowns
        combos = page.query_selector_all('[role="combobox"], [role="listbox"]')
        assert combos, "Expected at least one <select> or combobox element on work queue page for filtering/sorting"
    else:
        assert len(selects) >= 1, "Expected at least one <select> element on work queue page"
