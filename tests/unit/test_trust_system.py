"""Unit tests for trust_system helpers added in Task 1-2."""
import pytest
from python.helpers.settings_core import get_default_settings


def test_default_settings_has_trust_always_allow():
    s = get_default_settings()
    assert "trust_always_allow" in s
    assert isinstance(s["trust_always_allow"], list)
    assert s["trust_always_allow"] == []


def test_default_settings_has_trust_onboarded():
    s = get_default_settings()
    assert "trust_onboarded" in s
    assert s["trust_onboarded"] is False


def test_trust_always_allow_is_not_shared():
    s1 = get_default_settings()
    s2 = get_default_settings()
    s1["trust_always_allow"].append("some_tool")
    assert s2["trust_always_allow"] == [], (
        "get_default_settings() must return a fresh list each call"
    )
