"""E2E tests for skills API endpoints: skills_list, skills_get, skills_search."""

import urllib.error

import pytest

from tests.e2e.helpers import api_post_tolerant as api_post

pytestmark = [pytest.mark.e2e]


def test_skills_list_returns_array(app_server, auth_cookies):
    """POST skills_list with empty body returns a dict with a 'skills' list."""
    data = api_post(app_server, auth_cookies, "skills_list", {})
    assert "skills" in data, f"Expected 'skills' key in response: {data}"
    assert isinstance(data["skills"], list), f"Expected 'skills' to be a list: {data}"


def test_skills_list_with_category(app_server, auth_cookies):
    """POST skills_list with a nonexistent category returns an empty or partial list."""
    data = api_post(app_server, auth_cookies, "skills_list", {"category": "nonexistent_category_xyz"})
    assert "skills" in data, f"Expected 'skills' key in response: {data}"
    assert isinstance(data["skills"], list), f"Expected 'skills' to be a list: {data}"


def test_skills_get_missing_name(app_server, auth_cookies):
    """POST skills_get with no name field returns 400."""
    try:
        data = api_post(app_server, auth_cookies, "skills_get", {})
        raise AssertionError(f"Expected 400 error, got 200: {data}")
    except urllib.error.HTTPError as exc:
        assert exc.code == 400, f"Expected 400, got {exc.code}"


def test_skills_get_not_found(app_server, auth_cookies):
    """POST skills_get with a nonexistent skill name returns 404."""
    try:
        data = api_post(app_server, auth_cookies, "skills_get", {"name": "nonexistent_skill_xyz_999"})
        raise AssertionError(f"Expected 404 error, got 200: {data}")
    except urllib.error.HTTPError as exc:
        assert exc.code == 404, f"Expected 404, got {exc.code}"


def test_skills_get_valid(app_server, auth_cookies):
    """POST skills_get with a real skill name returns a skill dict.

    Fetches the skills list first; skips if no skills are installed.
    """
    list_data = api_post(app_server, auth_cookies, "skills_list", {})
    skills = list_data.get("skills", [])
    if not skills:
        pytest.skip("No skills installed; skipping skills_get valid test")

    first_skill = skills[0]
    # The skill entry may be a dict with a "name" key, or a plain string.
    if isinstance(first_skill, dict):
        skill_name = first_skill.get("name")
    else:
        skill_name = str(first_skill)

    assert skill_name, f"Could not determine skill name from first entry: {first_skill}"

    data = api_post(app_server, auth_cookies, "skills_get", {"name": skill_name})
    assert "skill" in data, f"Expected 'skill' key in response: {data}"
    assert isinstance(data["skill"], dict), f"Expected 'skill' to be a dict: {data}"


def test_skills_search_returns_results(app_server, auth_cookies):
    """POST skills_search with a query returns a dict with a 'results' list."""
    data = api_post(app_server, auth_cookies, "skills_search", {"query": "test"})
    assert "results" in data, f"Expected 'results' key in response: {data}"
    assert isinstance(data["results"], list), f"Expected 'results' to be a list: {data}"


def test_skills_search_missing_query(app_server, auth_cookies):
    """POST skills_search with no query field returns 400."""
    try:
        data = api_post(app_server, auth_cookies, "skills_search", {})
        raise AssertionError(f"Expected 400 error, got 200: {data}")
    except urllib.error.HTTPError as exc:
        assert exc.code == 400, f"Expected 400, got {exc.code}"
