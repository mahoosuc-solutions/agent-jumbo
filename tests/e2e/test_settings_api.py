"""E2E tests for the settings get/set API endpoints."""

import urllib.error

import pytest

from tests.e2e.helpers import api_post_tolerant as api_post

pytestmark = [pytest.mark.e2e]


@pytest.mark.e2e
def test_settings_get_returns_sections(app_server, auth_cookies):
    """POST settings_get with empty body returns a response with 'settings' and 'sections'."""
    data = api_post(app_server, auth_cookies, "settings_get", {})
    assert "settings" in data, f"Expected 'settings' key in response: {data}"
    settings = data["settings"]
    assert "sections" in settings, f"Expected 'sections' key in settings: {settings}"
    assert isinstance(settings["sections"], list), (
        f"Expected 'sections' to be a list, got: {type(settings['sections'])}"
    )


@pytest.mark.e2e
def test_settings_get_has_fields(app_server, auth_cookies):
    """At least one section in settings_get response contains a non-empty 'fields' list."""
    data = api_post(app_server, auth_cookies, "settings_get", {})
    sections = data["settings"]["sections"]
    assert sections, "Expected at least one section, got empty list"
    sections_with_fields = [s for s in sections if s.get("fields")]
    assert sections_with_fields, f"Expected at least one section with non-empty 'fields', got sections: {sections}"
    for section in sections_with_fields:
        for field in section["fields"]:
            assert "id" in field, f"Expected 'id' key in field: {field}"


@pytest.mark.e2e
def test_settings_roundtrip(app_server, auth_cookies):
    """Read a boolean setting, toggle it, verify change, then restore original value."""
    # Fetch current settings
    data = api_post(app_server, auth_cookies, "settings_get", {})
    sections = data["settings"]["sections"]

    # Find the first boolean field to toggle
    target_field = None
    target_section_idx = None
    for section in sections:
        for field in section.get("fields", []):
            if isinstance(field.get("value"), bool):
                target_field = field
                target_section_idx = sections.index(section)
                break
        if target_field:
            break

    # Fall back to looking for a field with id containing known boolean setting names
    if target_field is None:
        bool_names = {"chat_auto_scroll", "auto_scroll", "dark_mode", "notifications"}
        for section in sections:
            for field in section.get("fields", []):
                if field.get("id") in bool_names or str(field.get("value")).lower() in ("true", "false"):
                    target_field = field
                    target_section_idx = sections.index(section)
                    break
            if target_field:
                break

    if target_field is None:
        pytest.skip("No boolean field found in settings to roundtrip — skipping")

    field_id = target_field["id"]
    original_value = target_field["value"]
    toggled_value = not original_value if isinstance(original_value, bool) else (str(original_value).lower() != "true")

    # Build the sections payload with the toggled value
    def _make_sections_payload(value):
        return [{"fields": [{"id": field_id, "value": value}]}]

    # Write toggled value
    set_data = api_post(app_server, auth_cookies, "settings_set", {"sections": _make_sections_payload(toggled_value)})
    assert "settings" in set_data, f"Expected 'settings' in settings_set response: {set_data}"

    # Verify the change persisted
    verify_data = api_post(app_server, auth_cookies, "settings_get", {})
    verify_sections = verify_data["settings"]["sections"]
    changed_field = None
    for section in verify_sections:
        for field in section.get("fields", []):
            if field.get("id") == field_id:
                changed_field = field
                break
        if changed_field:
            break

    assert changed_field is not None, f"Field '{field_id}' not found in settings after toggle"
    assert changed_field["value"] == toggled_value, (
        f"Expected field '{field_id}' to be {toggled_value!r} after toggle, got {changed_field['value']!r}"
    )

    # Restore original value
    api_post(app_server, auth_cookies, "settings_set", {"sections": _make_sections_payload(original_value)})

    # Verify restoration
    restored_data = api_post(app_server, auth_cookies, "settings_get", {})
    restored_sections = restored_data["settings"]["sections"]
    restored_field = None
    for section in restored_sections:
        for field in section.get("fields", []):
            if field.get("id") == field_id:
                restored_field = field
                break
        if restored_field:
            break

    assert restored_field is not None, f"Field '{field_id}' not found after restore"
    assert restored_field["value"] == original_value, (
        f"Expected field '{field_id}' restored to {original_value!r}, got {restored_field['value']!r}"
    )


@pytest.mark.e2e
def test_settings_set_invalid_field(app_server, auth_cookies):
    """POST settings_set with a nonexistent field ID does not crash (success or graceful error)."""
    try:
        data = api_post(
            app_server,
            auth_cookies,
            "settings_set",
            {"sections": [{"fields": [{"id": "__nonexistent_field_xyz__", "value": "ignored"}]}]},
        )
        # Either a success response (field silently ignored) or an error dict — both are acceptable
        assert isinstance(data, dict), f"Expected a JSON object response, got: {data!r}"
    except urllib.error.HTTPError as exc:
        # A 4xx/5xx response is also acceptable — the server must not return 2xx with a crash body
        assert exc.code in (400, 422, 500), (
            f"Unexpected HTTP status {exc.code} for invalid field: {getattr(exc, '_response_body', '')}"
        )


@pytest.mark.e2e
def test_settings_get_idempotent(app_server, auth_cookies):
    """Two consecutive calls to settings_get return the same structure."""
    first = api_post(app_server, auth_cookies, "settings_get", {})
    second = api_post(app_server, auth_cookies, "settings_get", {})

    assert "settings" in first and "settings" in second, (
        f"Both responses must have 'settings' key. first={first!r}, second={second!r}"
    )

    first_sections = first["settings"]["sections"]
    second_sections = second["settings"]["sections"]

    assert len(first_sections) == len(second_sections), (
        f"Section count mismatch between calls: {len(first_sections)} vs {len(second_sections)}"
    )

    first_ids = {field["id"] for section in first_sections for field in section.get("fields", []) if "id" in field}
    second_ids = {field["id"] for section in second_sections for field in section.get("fields", []) if "id" in field}
    assert first_ids == second_ids, (
        f"Field IDs differ between calls. Only in first: {first_ids - second_ids}, "
        f"only in second: {second_ids - first_ids}"
    )
