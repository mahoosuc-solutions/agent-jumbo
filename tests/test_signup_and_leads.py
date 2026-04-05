"""
Tests for signup endpoint, signup dashboard, and signup_leads tool.
"""

import asyncio
import threading
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from flask import Flask


def _make_app():
    app = Flask(__name__)
    app.secret_key = "test-secret"  # pragma: allowlist secret
    return app


# ---------------------------------------------------------------------------
# SignupEndpoint
# ---------------------------------------------------------------------------


class TestSignupEndpoint:
    def test_valid_free_cloud_signup(self):
        from python.api.signup import SignupEndpoint

        app = _make_app()
        handler = SignupEndpoint(app, threading.Lock())
        with app.test_request_context(
            "/signup",
            method="POST",
            json={"email": "user@example.com", "plan": "free_cloud"},
        ) as ctx:
            resp = asyncio.run(handler.handle_request(ctx.request))

        body = resp.get_json()
        assert body["ok"] is True
        assert body["plan"] == "free_cloud"
        assert body["email"] == "user@example.com"
        assert "email_sent" in body
        assert "next_steps" in body

    def test_invalid_email_returns_400(self):
        from python.api.signup import SignupEndpoint

        app = _make_app()
        handler = SignupEndpoint(app, threading.Lock())
        with app.test_request_context(
            "/signup",
            method="POST",
            json={"email": "notanemail", "plan": "pro"},
        ) as ctx:
            resp = asyncio.run(handler.handle_request(ctx.request))

        assert resp.status_code == 400

    def test_unknown_plan_defaults_to_free_cloud(self):
        from python.api.signup import SignupEndpoint

        app = _make_app()
        handler = SignupEndpoint(app, threading.Lock())
        with app.test_request_context(
            "/signup",
            method="POST",
            json={"email": "user@example.com", "plan": "unicorn_plan"},
        ) as ctx:
            resp = asyncio.run(handler.handle_request(ctx.request))

        body = resp.get_json()
        assert body["plan"] == "free_cloud"

    def test_email_sent_true_when_smtp_configured(self):
        from python.api.signup import SignupEndpoint

        app = _make_app()
        handler = SignupEndpoint(app, threading.Lock())

        mock_sender = MagicMock()
        mock_sender.send_email = AsyncMock(return_value={"success": True})

        with (
            patch.dict(
                "os.environ",
                {
                    "SMTP_SERVER": "smtp.example.com",
                    "SMTP_PORT": "587",
                    "SMTP_USERNAME": "user",
                    "SMTP_PASSWORD": "pass",  # pragma: allowlist secret
                },
            ),
            patch("python.helpers.email_sender.EmailSender", return_value=mock_sender),
        ):
            with app.test_request_context(
                "/signup",
                method="POST",
                json={"email": "user@example.com", "plan": "pro"},
            ) as ctx:
                resp = asyncio.run(handler.handle_request(ctx.request))

        body = resp.get_json()
        assert body["ok"] is True
        assert body["email_sent"] is True

    def test_email_failure_does_not_fail_signup(self):
        from python.api.signup import SignupEndpoint

        app = _make_app()
        handler = SignupEndpoint(app, threading.Lock())

        mock_sender = MagicMock()
        mock_sender.send_email = AsyncMock(side_effect=RuntimeError("SMTP down"))

        with (
            patch.dict(
                "os.environ",
                {
                    "SMTP_SERVER": "smtp.example.com",
                    "SMTP_PORT": "587",
                    "SMTP_USERNAME": "user",
                    "SMTP_PASSWORD": "pass",  # pragma: allowlist secret
                },
            ),
            patch("python.helpers.email_sender.EmailSender", return_value=mock_sender),
        ):
            with app.test_request_context(
                "/signup",
                method="POST",
                json={"email": "user@example.com", "plan": "enterprise"},
            ) as ctx:
                resp = asyncio.run(handler.handle_request(ctx.request))

        body = resp.get_json()
        assert body["ok"] is True
        assert body["email_sent"] is False  # graceful failure


# ---------------------------------------------------------------------------
# SignupDashboard
# ---------------------------------------------------------------------------


class TestSignupDashboard:
    def test_empty_state_when_no_db(self, tmp_path):
        from python.api.signup_dashboard import SignupDashboard

        app = _make_app()
        handler = SignupDashboard(app, threading.Lock())

        # Point the module at a non-existent db
        with patch("python.api.signup_dashboard._DB_PATH", tmp_path / "nonexistent.db"):
            with app.test_request_context("/signup_dashboard", method="POST", json={}) as ctx:
                resp = asyncio.run(handler.handle_request(ctx.request))

        body = resp.get_json()
        assert body["success"] is True
        assert body["total"] == 0
        assert body["recent"] == []
        assert "note" in body

    def test_returns_required_keys(self, tmp_path):
        # Seed a signup into a temp db
        import sqlite3

        from python.api.signup_dashboard import SignupDashboard

        db = tmp_path / "signups.db"
        conn = sqlite3.connect(str(db))
        conn.execute(
            "CREATE TABLE signups (id TEXT, created_at TEXT, name TEXT, email TEXT, "
            "company TEXT, plan TEXT, source TEXT, referrer TEXT, metadata TEXT)"
        )
        conn.execute(
            "INSERT INTO signups VALUES ('id1','2026-04-05T10:00:00','Alice','a@b.com','','free_cloud','web','','{}')"
        )
        conn.commit()
        conn.close()

        app = _make_app()
        handler = SignupDashboard(app, threading.Lock())
        with patch("python.api.signup_dashboard._DB_PATH", db):
            with app.test_request_context("/signup_dashboard", method="POST", json={}) as ctx:
                resp = asyncio.run(handler.handle_request(ctx.request))

        body = resp.get_json()
        assert body["success"] is True
        assert body["total"] == 1
        assert body["by_plan"]["free_cloud"] == 1
        assert len(body["recent"]) == 1
        assert isinstance(body["daily_series"], list)


# ---------------------------------------------------------------------------
# SignupLeads tool (smoke — no real agent context needed)
# ---------------------------------------------------------------------------


class TestSignupLeadsTool:
    def _make_tool(self, tmp_db: Path):
        """Construct a SignupLeads instance with a patched DB path."""
        # Seed a temp db
        import sqlite3

        from python.tools.signup_leads import SignupLeads

        conn = sqlite3.connect(str(tmp_db))
        conn.execute(
            "CREATE TABLE signups (id TEXT, created_at TEXT, name TEXT, email TEXT, "
            "company TEXT, plan TEXT, source TEXT, referrer TEXT, metadata TEXT)"
        )
        for i, plan in enumerate(["free_cloud", "pro", "free_cloud"]):
            conn.execute(
                "INSERT INTO signups VALUES (?,?,?,?,?,?,?,?,?)",
                (f"id{i}", f"2026-04-0{i + 1}T10:00:00", f"User{i}", f"u{i}@x.com", "", plan, "web", "", "{}"),
            )
        conn.commit()
        conn.close()

        tool = SignupLeads.__new__(SignupLeads)
        tool.args = {}
        return tool

    def test_summary_action(self, tmp_path):
        db = tmp_path / "signups.db"
        tool = self._make_tool(db)
        tool.args = {"action": "summary", "days": "30"}
        with patch("python.tools.signup_leads._DB_PATH", db):
            result = asyncio.run(tool.execute())
        assert "3" in result.message or "total" in result.message.lower()

    def test_query_filters_by_plan(self, tmp_path):
        db = tmp_path / "signups.db"
        tool = self._make_tool(db)
        tool.args = {"action": "query", "plan": "pro"}
        with patch("python.tools.signup_leads._DB_PATH", db):
            result = asyncio.run(tool.execute())
        assert "pro" in result.message
        assert "free_cloud" not in result.message

    def test_export_csv_creates_file(self, tmp_path):
        db = tmp_path / "signups.db"
        tool = self._make_tool(db)
        tool.args = {"action": "export_csv"}
        with (
            patch("python.tools.signup_leads._DB_PATH", db),
            patch("python.tools.signup_leads._DB_PATH", db),
        ):
            # Also patch the export dir to tmp_path
            import python.tools.signup_leads as leads_mod

            orig = leads_mod._DB_PATH
            leads_mod._DB_PATH = db
            try:
                result = asyncio.run(tool.execute())
            finally:
                leads_mod._DB_PATH = orig

        assert "export" in result.message.lower()
        exports = list(tmp_path.glob("signups_export_*.csv"))
        assert len(exports) == 1
        assert exports[0].stat().st_size > 0

    def test_invalid_action(self, tmp_path):
        db = tmp_path / "signups.db"
        tool = self._make_tool(db)
        tool.args = {"action": "noop"}
        with patch("python.tools.signup_leads._DB_PATH", db):
            result = asyncio.run(tool.execute())
        assert "unknown action" in result.message.lower()
