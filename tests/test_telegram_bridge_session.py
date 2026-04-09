"""Tests for enhanced Telegram session state."""

from unittest.mock import patch

import pytest

from python.helpers.telegram_bridge import (
    clear_session_meta,
    get_session_meta,
    set_session_meta,
)


@pytest.fixture(autouse=True)
def mock_state(tmp_path):
    state_file = tmp_path / "telegram_state.json"
    state_file.write_text("{}")
    with patch("python.helpers.telegram_bridge.STATE_PATH", state_file):
        yield state_file


class TestSessionMeta:
    def test_set_and_get_meta(self):
        set_session_meta("chat123", "active_project", "agent-mahoo")
        assert get_session_meta("chat123", "active_project") == "agent-mahoo"

    def test_get_missing_key_returns_none(self):
        assert get_session_meta("chat123", "nonexistent") is None

    def test_clear_session_meta(self):
        set_session_meta("chat123", "last_tool", "portfolio")
        clear_session_meta("chat123")
        assert get_session_meta("chat123", "last_tool") is None

    def test_multiple_keys_per_chat(self):
        set_session_meta("chat123", "active_project", "proj-a")
        set_session_meta("chat123", "last_tool", "workflow_engine")
        assert get_session_meta("chat123", "active_project") == "proj-a"
        assert get_session_meta("chat123", "last_tool") == "workflow_engine"

    def test_vision_context_stored(self):
        set_session_meta(
            "chat123",
            "vision_context",
            {
                "description": "A kanban board showing 3 columns",
                "extracted_items": ["task-1", "task-2"],
            },
        )
        ctx = get_session_meta("chat123", "vision_context")
        assert ctx["description"] == "A kanban board showing 3 columns"
        assert len(ctx["extracted_items"]) == 2

    def test_vision_context_overwrites_on_new_image(self):
        set_session_meta("chat123", "vision_context", {"description": "Old image"})
        set_session_meta("chat123", "vision_context", {"description": "New image"})
        stored = get_session_meta("chat123", "vision_context")
        assert stored["description"] == "New image"
