"""Tests for identity database — local user registration."""

import os
import tempfile

import pytest


@pytest.fixture
def db():
    """Create a temporary identity database for testing."""
    from python.helpers.identity_db import IdentityDatabase

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        yield IdentityDatabase(db_path)
    finally:
        os.unlink(db_path)


class TestLocalUserCreation:
    """Tests for create_local_user and lookup methods."""

    def test_create_user(self, db):
        user = db.create_local_user("u1", "test@example.com", "hashed_pw", "Test User")  # pragma: allowlist secret

        assert user["user_id"] == "u1"
        assert user["email"] == "test@example.com"
        assert user["full_name"] == "Test User"
        assert user["password_hash"] == "hashed_pw"  # pragma: allowlist secret
        assert user["role"] == "operator"

    def test_get_user_by_email(self, db):
        db.create_local_user("u2", "find@example.com", "pw", "Finder")

        found = db.get_user_by_email("find@example.com")
        assert found is not None
        assert found["user_id"] == "u2"

    def test_get_user_by_email_case_insensitive(self, db):
        db.create_local_user("u3", "Case@Example.COM", "pw", "Case")

        found = db.get_user_by_email("case@example.com")
        assert found is not None
        assert found["user_id"] == "u3"

    def test_get_user_by_email_not_found(self, db):
        assert db.get_user_by_email("nobody@example.com") is None

    def test_get_user_by_id(self, db):
        db.create_local_user("u4", "byid@example.com", "pw", "ByID")

        found = db.get_user_by_id("u4")
        assert found is not None
        assert found["email"] == "byid@example.com"

    def test_get_user_by_id_not_found(self, db):
        assert db.get_user_by_id("nonexistent") is None

    def test_upsert_on_conflict(self, db):
        db.create_local_user("u5", "old@example.com", "old_pw", "Old")
        db.create_local_user("u5", "new@example.com", "new_pw", "New")

        user = db.get_user_by_id("u5")
        assert user["email"] == "new@example.com"
        assert user["password_hash"] == "new_pw"  # pragma: allowlist secret
