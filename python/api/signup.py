"""
Signup handler — captures Free Cloud and paid plan signups.
Stores lead in SQLite, returns confirmation with next-step instructions.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from python.helpers.api import ApiHandler

_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "signups.db"

_PLAN_NEXT_STEPS = {
    "free_cloud": {
        "headline": "You're on the list for Free Cloud.",
        "body": (
            "We'll email you access credentials within 1 business day. "
            "In the meantime, you can explore the live demos or read the install guide."
        ),
        "actions": [
            {"label": "Try the demos", "href": "/try"},
            {"label": "Read the docs", "href": "/documentation"},
        ],
    },
    "pro": {
        "headline": "Pro plan — let's get you set up.",
        "body": ("Check your email for a setup link. If you'd like to go straight to checkout, use the button below."),
        "actions": [
            {"label": "Go to checkout", "href": "/billing/checkout?plan=pro"},
            {"label": "Try the demos first", "href": "/try"},
        ],
    },
    "enterprise": {
        "headline": "Enterprise plan — we'll be in touch.",
        "body": (
            "An account manager will reach out within 1 business day to schedule onboarding. "
            "You can also book time directly."
        ),
        "actions": [
            {"label": "Book a call", "href": "/demo"},
            {"label": "Try the demos", "href": "/try"},
        ],
    },
    "community": {
        "headline": "Self-hosted Community edition — free forever.",
        "body": "Follow the install guide to get running in minutes. No account needed.",
        "actions": [
            {"label": "Open install guide", "href": "/install"},
            {"label": "Read the docs", "href": "/documentation"},
        ],
    },
}


def _get_db() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signups (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            name TEXT,
            email TEXT NOT NULL,
            company TEXT,
            plan TEXT NOT NULL,
            source TEXT,
            referrer TEXT,
            metadata TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_signups_email ON signups(email)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_signups_plan ON signups(plan)")
    conn.commit()
    return conn


class SignupEndpoint(ApiHandler):
    async def process(self, input: dict, files: list) -> dict:
        email = (input.get("email") or "").strip().lower()
        name = (input.get("name") or "").strip()
        company = (input.get("company") or "").strip()
        plan = (input.get("plan") or "free_cloud").strip().lower()
        source = (input.get("source") or "website").strip()
        referrer = (input.get("referrer") or "").strip()

        if not email or "@" not in email:
            return {"error": "valid email is required"}, 400  # type: ignore[return-value]

        valid_plans = set(_PLAN_NEXT_STEPS.keys())
        if plan not in valid_plans:
            plan = "free_cloud"

        signup_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        try:
            conn = _get_db()
            conn.execute(
                "INSERT OR IGNORE INTO signups (id, created_at, name, email, company, plan, source, referrer, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (signup_id, now, name, email, company, plan, source, referrer, json.dumps({})),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass  # Don't fail the user if DB write fails

        next_steps = _PLAN_NEXT_STEPS.get(plan, _PLAN_NEXT_STEPS["free_cloud"])

        return {
            "ok": True,
            "signup_id": signup_id,
            "plan": plan,
            "email": email,
            "next_steps": next_steps,
        }
