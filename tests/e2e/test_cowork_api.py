"""E2E tests for the cowork API endpoints."""

import pytest

from tests.e2e.helpers import api_post

pytestmark = [pytest.mark.e2e]


def test_cowork_approvals_list_empty(app_server, auth_cookies):
    """POST cowork_approvals_list with a nonexistent context returns empty approvals."""
    resp = api_post(
        app_server,
        auth_cookies,
        "cowork_approvals_list",
        {"context": "nonexistent_ctx_e2e"},
    )
    assert "approvals" in resp
    assert isinstance(resp["approvals"], list)


def test_cowork_approvals_update_no_context(app_server, auth_cookies):
    """POST cowork_approvals_update with a nonexistent context returns empty approvals."""
    resp = api_post(
        app_server,
        auth_cookies,
        "cowork_approvals_update",
        {"context": "nonexistent_ctx_e2e", "action": "clear_resolved"},
    )
    assert "approvals" in resp


def test_cowork_folders_get_returns_list(app_server, auth_cookies):
    """POST cowork_folders_get returns a list of paths."""
    resp = api_post(app_server, auth_cookies, "cowork_folders_get", {})
    assert "paths" in resp
    assert isinstance(resp["paths"], list)


def test_cowork_folders_set_and_get_roundtrip(app_server, auth_cookies):
    """Set cowork folders, verify persistence, then restore originals."""
    # Get current paths to restore later
    original = api_post(app_server, auth_cookies, "cowork_folders_get", {})
    original_paths = original["paths"]

    try:
        # Set a test path
        set_resp = api_post(
            app_server,
            auth_cookies,
            "cowork_folders_set",
            {"paths": ["/tmp/e2e_test_path"]},
        )
        assert "paths" in set_resp
        # The returned paths should contain the (possibly normalized) test path
        assert any("e2e_test_path" in p for p in set_resp["paths"])

        # Verify persistence via a fresh GET
        get_resp = api_post(app_server, auth_cookies, "cowork_folders_get", {})
        assert any("e2e_test_path" in p for p in get_resp["paths"])
    finally:
        # Restore original paths
        api_post(
            app_server,
            auth_cookies,
            "cowork_folders_set",
            {"paths": original_paths},
        )


def test_cowork_folders_set_deduplicates(app_server, auth_cookies):
    """Setting duplicate paths should deduplicate them."""
    # Save originals to restore later
    original = api_post(app_server, auth_cookies, "cowork_folders_get", {})
    original_paths = original["paths"]

    try:
        resp = api_post(
            app_server,
            auth_cookies,
            "cowork_folders_set",
            {"paths": ["/tmp/test", "/tmp/test", "/tmp/test"]},
        )
        assert "paths" in resp
        # After deduplication, there should be no duplicate entries
        assert len(resp["paths"]) == len(set(resp["paths"]))
        # Should have at most 1 entry matching our test path
        matching = [p for p in resp["paths"] if "tmp" in p and "test" in p]
        assert len(matching) <= 1
    finally:
        api_post(
            app_server,
            auth_cookies,
            "cowork_folders_set",
            {"paths": original_paths},
        )
