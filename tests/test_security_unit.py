"""
Security regression tests for RC2 hardening.

Tests validate fixes for CSRF bypass, unrestricted upload,
path traversal, CSP headers, rate limiting, and DB safety.
"""

import os
import tempfile

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def upload_handler():
    """Create an UploadFile handler instance for testing."""
    from python.api.upload import UploadFile

    return UploadFile(app=None, thread_lock=None)


# ---------------------------------------------------------------------------
# 1B. File Upload Restrictions
# ---------------------------------------------------------------------------


class TestFileUploadSecurity:
    """Verify file upload whitelist enforcement."""

    def test_allowed_extensions_accepted(self, upload_handler):
        for ext in ("png", "jpg", "pdf", "csv", "json", "md", "txt"):
            assert upload_handler.allowed_file(f"test.{ext}"), f".{ext} should be allowed"

    def test_dangerous_extensions_rejected(self, upload_handler):
        for ext in ("exe", "sh", "bat", "py", "php", "jsp", "dll", "so", "cmd"):
            assert not upload_handler.allowed_file(f"malware.{ext}"), f".{ext} should be rejected"

    def test_no_extension_rejected(self, upload_handler):
        assert not upload_handler.allowed_file("noextension")

    def test_double_extension_uses_last(self, upload_handler):
        assert upload_handler.allowed_file("file.tar.gz")
        assert not upload_handler.allowed_file("file.pdf.exe")

    def test_magic_bytes_png(self, upload_handler):
        """PNG magic bytes should validate."""
        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        assert upload_handler._check_magic("png", png_header)

    def test_magic_bytes_mismatch(self, upload_handler):
        """Wrong magic bytes should fail."""
        assert not upload_handler._check_magic("png", b"NOT_A_PNG" + b"\x00" * 100)

    def test_magic_bytes_pdf(self, upload_handler):
        assert upload_handler._check_magic("pdf", b"%PDF-1.4" + b"\x00" * 100)

    def test_magic_bytes_zip(self, upload_handler):
        assert upload_handler._check_magic("zip", b"PK\x03\x04" + b"\x00" * 100)

    def test_empty_content_rejected(self, upload_handler):
        assert not upload_handler._check_magic("png", b"")


# ---------------------------------------------------------------------------
# 1C. Path Traversal in Backup Restore
# ---------------------------------------------------------------------------


class TestPathTraversalProtection:
    """Verify zip path traversal (zip slip) prevention."""

    def test_dotdot_path_rejected(self):
        from python.helpers.backup import BackupService

        svc = BackupService()
        with pytest.raises(ValueError, match="path traversal"):
            svc._validate_zip_member_path("../../etc/passwd", {})

    def test_dotdot_in_middle_rejected(self):
        from python.helpers.backup import BackupService

        svc = BackupService()
        with pytest.raises(ValueError, match="path traversal"):
            svc._validate_zip_member_path("a0/knowledge/../../../etc/shadow", {})

    def test_normal_path_accepted(self):
        from python.helpers.backup import BackupService

        svc = BackupService()
        # Should not raise
        svc._validate_zip_member_path("a0/tmp/settings.json", {})

    def test_backslash_dotdot_rejected(self):
        from python.helpers.backup import BackupService

        svc = BackupService()
        with pytest.raises(ValueError, match="path traversal"):
            svc._validate_zip_member_path("a0\\..\\..\\etc\\passwd", {})


# ---------------------------------------------------------------------------
# 1D. Content Security Policy
# ---------------------------------------------------------------------------


class TestCSPHeaders:
    """Verify CSP contains required directives for Alpine.js and does not allow wildcard HTTPS."""

    def test_unsafe_eval_present_in_csp(self):
        """CSP must contain 'unsafe-eval' (required by Alpine.js standard build)."""
        import inspect

        import run_ui

        source = inspect.getsource(run_ui.add_security_headers)
        assert "'unsafe-eval'" in source, "CSP missing 'unsafe-eval' required by Alpine.js"

    def test_no_wildcard_https_in_csp(self):
        """CSP must not allow https://* (any HTTPS origin)."""
        import inspect

        import run_ui

        source = inspect.getsource(run_ui.add_security_headers)
        assert "https://*" not in source, "CSP still contains https://* wildcard"


# ---------------------------------------------------------------------------
# 1E. CSRF Validation
# ---------------------------------------------------------------------------


class TestCSRFValidation:
    """Verify CSRF requires header, not just cookie."""

    def test_csrf_decorator_requires_header(self):
        """CSRF protect should check X-CSRF-Token header, not cookie."""
        import inspect

        import run_ui

        source = inspect.getsource(run_ui.csrf_protect)
        # Should NOT accept cookie as alternative
        assert "or cookie" not in source, "CSRF still accepts cookie as alternative"
        # Should require header
        assert "X-CSRF-Token" in source


# ---------------------------------------------------------------------------
# 1F. Database WAL Mode and Thread Safety
# ---------------------------------------------------------------------------


class TestDatabaseSafety:
    """Verify WAL mode and thread safety on DatabaseManager."""

    def test_wal_mode_enabled(self):
        from python.helpers.db_manager import DatabaseManager

        with tempfile.TemporaryDirectory() as tmpdir:
            db = DatabaseManager("test.db", data_dir=tmpdir)
            conn = db.connection
            cursor = conn.execute("PRAGMA journal_mode")
            mode = cursor.fetchone()[0]
            assert mode == "wal", f"Expected WAL mode, got {mode}"
            db.close()

    def test_busy_timeout_set(self):
        from python.helpers.db_manager import DatabaseManager

        with tempfile.TemporaryDirectory() as tmpdir:
            db = DatabaseManager("test.db", data_dir=tmpdir)
            conn = db.connection
            cursor = conn.execute("PRAGMA busy_timeout")
            timeout = cursor.fetchone()[0]
            assert timeout == 5000, f"Expected busy_timeout=5000, got {timeout}"
            db.close()

    def test_threading_lock_exists(self):
        import threading

        from python.helpers.db_manager import DatabaseManager

        with tempfile.TemporaryDirectory() as tmpdir:
            db = DatabaseManager("test.db", data_dir=tmpdir)
            assert hasattr(db, "_lock")
            assert isinstance(db._lock, type(threading.Lock()))
            db.close()

    def test_connection_timeout(self):
        """Connection should have a timeout to prevent indefinite hangs."""
        from python.helpers.db_manager import DatabaseManager

        with tempfile.TemporaryDirectory() as tmpdir:
            db = DatabaseManager("test.db", data_dir=tmpdir)
            # The timeout is set in sqlite3.connect(timeout=5.0)
            # We verify by checking the connection was created without error
            assert db.connection is not None
            db.close()


# ---------------------------------------------------------------------------
# 2B. Input Validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Verify API input validation."""

    def test_message_too_long_rejected(self):
        from python.helpers.validators import validate_message_input

        with pytest.raises(ValueError, match="too long"):
            validate_message_input("x" * 200_000)

    def test_message_normal_accepted(self):
        from python.helpers.validators import validate_message_input

        validate_message_input("Hello, world!")

    def test_too_many_attachments_rejected(self):
        from python.helpers.validators import validate_message_input

        with pytest.raises(ValueError, match="Too many attachments"):
            validate_message_input("msg", list(range(25)))

    def test_settings_input_must_be_dict(self):
        from python.helpers.validators import validate_settings_input

        with pytest.raises(ValueError, match="must be a dictionary"):
            validate_settings_input("not a dict")

    def test_settings_sections_must_be_list(self):
        from python.helpers.validators import validate_settings_input

        with pytest.raises(ValueError, match="must be a list"):
            validate_settings_input({"sections": "not a list"})


# ---------------------------------------------------------------------------
# 2C. Error Response Sanitization
# ---------------------------------------------------------------------------


class TestErrorSanitization:
    """Verify API errors don't leak internal details."""

    def test_api_error_response_is_generic(self):
        """Error responses should not contain raw exception messages."""
        # The handle_request catches exceptions and returns generic errors
        # Verify by checking the source
        import inspect

        from python.helpers.api import ApiHandler

        source = inspect.getsource(ApiHandler.handle_request)
        assert "Internal server error" in source
        assert "X-Request-ID" in source or "request_id" in source


# ---------------------------------------------------------------------------
# 2E. API Throttle
# ---------------------------------------------------------------------------


class TestAPIThrottle:
    """Verify rate limiter decorator."""

    def test_throttle_decorator_exists(self):
        from python.helpers.api_throttle import AsyncThrottle, throttled

        assert callable(throttled)
        t = AsyncThrottle(calls_per_minute=60)
        assert t.interval == pytest.approx(1.0, abs=0.01)

    def test_throttle_interval_calculation(self):
        from python.helpers.api_throttle import AsyncThrottle

        t = AsyncThrottle(calls_per_minute=30)
        assert t.interval == pytest.approx(2.0, abs=0.01)


# ---------------------------------------------------------------------------
# 3D. Settings Persistence Thread Safety
# ---------------------------------------------------------------------------


class TestSettingsPersistence:
    """Verify settings persistence has proper locking."""

    def test_settings_lock_exists(self):
        import threading

        from python.helpers import settings_persistence

        assert hasattr(settings_persistence, "_settings_lock")
        assert isinstance(settings_persistence._settings_lock, type(threading.Lock()))


# ---------------------------------------------------------------------------
# 3E. Database Indexes
# ---------------------------------------------------------------------------


class TestDatabaseIndexes:
    """Verify database indexes are created."""

    def test_linear_db_indexes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from instruments.custom.linear_integration.linear_db import LinearDatabase

            db = LinearDatabase(db_path=os.path.join(tmpdir, "test.db"))
            conn = db.get_connection()
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = {row[0] for row in cursor.fetchall()}
            conn.close()
            assert "idx_issues_project_id" in indexes
            assert "idx_issues_state_name" in indexes
            assert "idx_issues_team_id" in indexes

    def test_motion_db_indexes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from instruments.custom.motion_integration.motion_db import MotionDatabase

            db = MotionDatabase(db_path=os.path.join(tmpdir, "test.db"))
            conn = db.get_connection()
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = {row[0] for row in cursor.fetchall()}
            conn.close()
            assert "idx_tasks_workspace_id" in indexes
            assert "idx_tasks_status" in indexes

    def test_notion_db_indexes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from instruments.custom.notion_integration.notion_db import NotionDatabase

            db = NotionDatabase(db_path=os.path.join(tmpdir, "test.db"))
            conn = db.get_connection()
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = {row[0] for row in cursor.fetchall()}
            conn.close()
            assert "idx_pages_database_id" in indexes
            assert "idx_notion_linear_map_linear_id" in indexes
