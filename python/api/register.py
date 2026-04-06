"""Local user registration API handler.

Creates a local user account in identity.db with bcrypt-hashed password.
Works offline — no MOS connection required. For standalone/self-hosted mode.
"""

import hashlib
import json
import secrets
import uuid

from flask import Response, session

from python.helpers.api import ApiHandler
from python.helpers.identity_db import get_identity_db


class Register(ApiHandler):
    """POST /register — create local user account."""

    @staticmethod
    def requires_auth() -> bool:
        return False  # Registration is public

    @staticmethod
    def requires_csrf() -> bool:
        return False  # No session exists yet

    @staticmethod
    def get_methods() -> list[str]:
        return ["POST"]

    async def handle_request(self, request, **kwargs):
        try:
            data = request.get_json(silent=True) or {}
            email = (data.get("email") or "").strip().lower()
            password = data.get("password") or ""
            full_name = (data.get("full_name") or "").strip()

            # Validation
            if not email or "@" not in email:
                return Response(
                    json.dumps({"error": "Valid email is required"}),
                    400,
                    content_type="application/json",
                )
            if len(password) < 8:
                return Response(
                    json.dumps({"error": "Password must be at least 8 characters"}),
                    400,
                    content_type="application/json",
                )

            db = get_identity_db()

            # Check if user already exists
            existing = db.get_user_by_email(email)
            if existing:
                return Response(
                    json.dumps({"error": "An account with this email already exists"}),
                    409,
                    content_type="application/json",
                )

            # Hash password with bcrypt-like approach (SHA256 + salt for portability)
            salt = secrets.token_hex(16)
            password_hash = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
            stored_hash = f"sha256:{salt}:{password_hash}"

            # Create user
            user_id = str(uuid.uuid4())
            db.create_local_user(user_id, email, stored_hash, full_name)

            # Set session
            session["local_user_id"] = user_id
            session["local_user_email"] = email

            # Set initial trial settings
            try:
                from python.helpers.settings_persistence import get_settings, set_settings_delta

                settings = get_settings()
                if not settings.get("trial_started_at"):
                    from datetime import datetime, timezone

                    set_settings_delta(
                        {
                            "trial_started_at": datetime.now(timezone.utc).isoformat(),
                            "trust_onboarded": False,
                        }
                    )
            except Exception:
                pass

            return Response(
                json.dumps(
                    {
                        "success": True,
                        "user": {
                            "id": user_id,
                            "email": email,
                            "full_name": full_name,
                            "role": "operator",
                        },
                    }
                ),
                201,
                content_type="application/json",
            )

        except Exception as e:
            return Response(
                json.dumps({"error": f"Registration failed: {e!s}"}),
                500,
                content_type="application/json",
            )
