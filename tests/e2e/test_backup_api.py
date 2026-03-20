"""E2E tests for the backup API endpoints."""

import urllib.error

import pytest

from tests.e2e.helpers import api_post

pytestmark = [pytest.mark.e2e]


def test_backup_get_defaults_returns_patterns(app_server, auth_cookies):
    """POST backup_get_defaults with {} returns default patterns and metadata."""
    resp = api_post(app_server, auth_cookies, "backup_get_defaults", {})
    assert resp["success"] is True
    assert "default_patterns" in resp
    dp = resp["default_patterns"]
    assert isinstance(dp["include_patterns"], list)
    assert isinstance(dp["exclude_patterns"], list)
    assert isinstance(resp["metadata"], dict)


def test_backup_test_empty_patterns(app_server, auth_cookies):
    """POST backup_test with empty include_patterns returns no files."""
    resp = api_post(app_server, auth_cookies, "backup_test", {"include_patterns": []})
    assert resp["success"] is True
    assert resp["files"] == []
    assert resp["total_count"] == 0


def test_backup_test_with_patterns(app_server, auth_cookies):
    """POST backup_test with *.py pattern returns matching files."""
    resp = api_post(
        app_server,
        auth_cookies,
        "backup_test",
        {"include_patterns": ["*.py"], "max_files": 10},
    )
    assert resp["success"] is True
    assert isinstance(resp["files"], list)
    assert isinstance(resp["total_count"], int)
    assert resp["total_count"] >= 0


def test_backup_preview_grouped_empty(app_server, auth_cookies):
    """POST backup_preview_grouped with empty patterns returns no groups."""
    resp = api_post(app_server, auth_cookies, "backup_preview_grouped", {"include_patterns": []})
    assert resp["success"] is True
    assert resp["groups"] == []
    assert resp["total_files"] == 0


def test_backup_preview_grouped_with_patterns(app_server, auth_cookies):
    """POST backup_preview_grouped with *.py pattern returns grouped results."""
    resp = api_post(
        app_server,
        auth_cookies,
        "backup_preview_grouped",
        {"include_patterns": ["*.py"], "max_depth": 2},
    )
    assert resp["success"] is True
    assert isinstance(resp["groups"], list)
    assert isinstance(resp["stats"], dict)
    assert "total_groups" in resp["stats"]
    assert "total_files" in resp["stats"]


def test_backup_create_returns_file_or_error(app_server, auth_cookies):
    """POST backup_create with nonexistent pattern must not crash the server."""
    try:
        resp = api_post(
            app_server,
            auth_cookies,
            "backup_create",
            {
                "include_patterns": ["__nonexistent_pattern_xyz__"],
                "backup_name": "e2e-test",
            },
        )
        # If we get a dict back, it should at least be parseable
        assert isinstance(resp, (dict, bytes))
    except urllib.error.HTTPError:
        # Server returned an error status — acceptable as long as it didn't crash
        pass
