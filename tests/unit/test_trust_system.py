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


from python.helpers.trust_system import (
    get_approval_fingerprint,
    is_always_allowed,
    TRUST_ALWAYS_ALLOW_KEY,
)


def test_get_approval_fingerprint_uses_tool_name_and_first_arg():
    fp = get_approval_fingerprint("email_advanced", {"to": "a@b.com", "subject": "hi"})
    assert fp == "email_advanced:a@b.com"


def test_get_approval_fingerprint_no_args():
    fp = get_approval_fingerprint("memory_delete", {})
    assert fp == "memory_delete:"


def test_is_always_allowed_true():
    settings = {TRUST_ALWAYS_ALLOW_KEY: ["email_advanced", "code_execution_tool"]}
    assert is_always_allowed("email_advanced", settings) is True


def test_is_always_allowed_false():
    settings = {TRUST_ALWAYS_ALLOW_KEY: ["memory_delete"]}
    assert is_always_allowed("email_advanced", settings) is False


def test_is_always_allowed_empty_list():
    settings = {TRUST_ALWAYS_ALLOW_KEY: []}
    assert is_always_allowed("email_advanced", settings) is False


def test_is_always_allowed_missing_key():
    assert is_always_allowed("email_advanced", {}) is False
