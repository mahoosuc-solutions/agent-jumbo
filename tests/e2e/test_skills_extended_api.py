import urllib.error

import pytest

from tests.e2e.helpers import api_post

pytestmark = [pytest.mark.e2e]


def test_skills_scan_missing_params(app_server, auth_cookies):
    try:
        data = api_post(app_server, auth_cookies, "skills_scan", {})
        raise AssertionError(f"Expected HTTP error, got 200: {data}")
    except urllib.error.HTTPError as exc:
        assert exc.code == 400, f"Expected 400, got {exc.code}"


def test_skills_install_missing_path(app_server, auth_cookies):
    try:
        data = api_post(app_server, auth_cookies, "skills_install", {})
        raise AssertionError(f"Expected HTTP error, got 200: {data}")
    except urllib.error.HTTPError as exc:
        assert exc.code == 400, f"Expected 400, got {exc.code}"


def test_skills_uninstall_not_found(app_server, auth_cookies):
    try:
        data = api_post(app_server, auth_cookies, "skills_uninstall", {"name": "nonexistent_skill_xyz_999"})
        raise AssertionError(f"Expected HTTP error, got 200: {data}")
    except urllib.error.HTTPError as exc:
        assert exc.code == 404, f"Expected 404, got {exc.code}"


def test_skills_toggle_not_found(app_server, auth_cookies):
    try:
        data = api_post(app_server, auth_cookies, "skills_toggle", {"name": "nonexistent_skill_xyz_999"})
        raise AssertionError(f"Expected HTTP error, got 200: {data}")
    except urllib.error.HTTPError as exc:
        assert exc.code == 404, f"Expected 404, got {exc.code}"
