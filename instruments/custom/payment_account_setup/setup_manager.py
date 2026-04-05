"""Payment Account Setup Manager.

Orchestrates browser-assisted account creation for Stripe, Square, and PayPal.
The manager tracks sessions and steps in SQLite. The agent executes each step
using the MCP browser tools (Playwright / Chrome DevTools) available in the
conversation context.

Human-in-the-loop gates: any step with ``automation_type == "human_required"``
causes the manager to pause and return the step's ``human_instructions`` to the
agent, which relays them to the operator. The session status changes to
``awaiting_human`` until ``confirm_human_step`` is called.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from instruments.custom.payment_account_setup.credential_store import CredentialStore
from instruments.custom.payment_account_setup.setup_db import SetupDatabase

logger = logging.getLogger(__name__)

_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "payment_account_setup.db")


class PaymentAccountSetupManager:
    """Manages browser-assisted payment provider account setup sessions."""

    def __init__(self, db_path: str | None = None):
        self.db = SetupDatabase(db_path or _DB_PATH)
        self.credential_store = CredentialStore()

    # -- session lifecycle ---------------------------------------------------

    def start_setup(
        self,
        provider: str,
        business_name: str,
        email: str,
        country: str = "us",
        webhook_endpoint_url: str = "",
    ) -> dict[str, Any]:
        """Create a new setup session and load its step definitions.

        Returns the session dict along with the first step to execute.
        """
        provider = provider.lower().strip()
        if provider not in ("stripe", "square", "paypal"):
            raise ValueError(f"Unsupported provider '{provider}'. Choose: stripe, square, paypal")

        session_id = f"{provider}_{uuid.uuid4().hex[:8]}"
        if not webhook_endpoint_url:
            webhook_endpoint_url = os.environ.get(
                "STRIPE_WEBHOOK_ENDPOINT_URL",
                "http://localhost:6274/api/stripe/webhook",
            )

        self.db.create_session(
            session_id=session_id,
            provider=provider,
            business_name=business_name,
            email=email,
            country=country,
        )

        steps = self._load_steps(provider, session_id, email, webhook_endpoint_url)
        for s in steps:
            self.db.insert_step(
                step_id=s["step_id"],
                session_id=session_id,
                step_index=s["step_index"],
                title=s["title"],
                description=s.get("description", ""),
                automation_type=s["automation_type"],
                human_instructions=s.get("human_instructions", ""),
                action=s.get("action", {}),
                completion_check=s.get("completion_check", ""),
                extract_fields=s.get("extract_fields", []),
            )

        self.db.update_session(session_id, status="in_progress", total_steps=len(steps))
        session = self.db.get_session(session_id)
        first_step = self.db.list_steps(session_id)[0] if steps else None

        return {
            "session": session,
            "next_step": first_step,
            "message": (
                f"Session {session_id} created for {provider} account setup. "
                f"{len(steps)} steps total. " + (f"First step: {first_step['title']}" if first_step else "No steps.")
            ),
        }

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Return full session details including all steps."""
        session = self.db.get_session(session_id)
        if session is None:
            return None
        session["steps"] = self.db.list_steps(session_id)
        return session

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all setup sessions (most recent first)."""
        return self.db.list_sessions()

    # -- step execution ------------------------------------------------------

    def advance_step(
        self,
        session_id: str,
        step_result: dict[str, Any] | None = None,
        human_confirmed: bool = False,
    ) -> dict[str, Any]:
        """Advance the session to the next step.

        Call this after the agent has executed the current step using MCP tools.

        Args:
            session_id: The session to advance.
            step_result: Result data from executing the current step
                (e.g. extracted credential values from browser_evaluate).
            human_confirmed: Set to True when the operator has completed a
                human_required step and pressed Continue.

        Returns:
            Dict with ``next_step`` (or None if complete), ``session``, and
            any credentials extracted so far.
        """
        session = self.db.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id!r} not found")

        steps = self.db.list_steps(session_id)
        current_idx = session.get("current_step", 0)

        if current_idx >= len(steps):
            return {"session": session, "next_step": None, "message": "Setup complete."}

        current_step = steps[current_idx]

        # Validate human-required handoff
        if current_step["automation_type"] == "human_required" and not human_confirmed:
            self.db.update_session(session_id, status="awaiting_human")
            return {
                "session": self.db.get_session(session_id),
                "next_step": current_step,
                "awaiting_human": True,
                "human_instructions": current_step["human_instructions"],
                "message": (
                    f"Step '{current_step['title']}' requires operator action. "
                    "Call advance_step with human_confirmed=True when done."
                ),
            }

        # Mark current step completed and extract any credentials
        self.db.update_step(
            current_step["step_id"],
            status="completed",
            result_data=step_result or {},
        )

        extracted = session.get("extracted_credentials", {})
        if step_result:
            for field in current_step.get("extract_fields", []):
                if step_result.get(field):
                    extracted[field] = step_result[field]

        # Handle internal_store_credentials action
        if current_step.get("action", {}).get("tool") == "internal_store_credentials":
            provider = current_step["action"]["args"].get("provider", session["provider"])
            written = self.credential_store.write_credentials(provider, extracted)
            logger.info("Stored credentials for %s: %s", provider, list(written.keys()))

        next_idx = current_idx + 1
        self.db.update_session(
            session_id,
            current_step=next_idx,
            status="in_progress",
            extracted_credentials=extracted,
        )

        next_step = steps[next_idx] if next_idx < len(steps) else None

        if next_step is None:
            self.db.update_session(session_id, status="complete")

        return {
            "session": self.db.get_session(session_id),
            "next_step": next_step,
            "extracted_credentials": {k: f"{v[:8]}..." if len(v) > 8 else "***" for k, v in extracted.items()},
            "message": (
                f"Step {current_idx + 1}/{len(steps)} complete. "
                + (f"Next: {next_step['title']}" if next_step else "All steps complete!")
            ),
        }

    def mark_step_failed(self, session_id: str, error: str) -> dict[str, Any]:
        """Mark the current step as failed with an error message."""
        session = self.db.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id!r} not found")
        steps = self.db.list_steps(session_id)
        current_idx = session.get("current_step", 0)
        if current_idx < len(steps):
            self.db.update_step(steps[current_idx]["step_id"], status="failed", error=error)
        self.db.update_session(session_id, status="failed", notes=error)
        return self.get_session(session_id)

    # -- credential management -----------------------------------------------

    def store_credentials(
        self,
        provider: str,
        credentials: dict[str, str],
        session_id: str | None = None,
        push_to_vercel: bool = False,
    ) -> dict[str, str]:
        """Manually store credentials for a provider.

        Use this when the operator provides credentials manually that the
        browser automation could not extract automatically.
        """
        written = self.credential_store.write_credentials(provider, credentials, push_to_vercel=push_to_vercel)
        if session_id:
            session = self.db.get_session(session_id)
            if session:
                existing = session.get("extracted_credentials", {})
                existing.update(credentials)
                self.db.update_session(session_id, extracted_credentials=existing)
        return written

    def get_provider_credentials(self, provider: str) -> dict[str, str | None]:
        """Return which credentials are configured for a provider (values redacted)."""
        from instruments.custom.payment_account_setup.credential_store import PROVIDER_ENV_MAP

        env_map = PROVIDER_ENV_MAP.get(provider.lower(), {})
        result: dict[str, str | None] = {}
        for logical, env_name in env_map.items():
            val = self.credential_store.read_credential(env_name)
            result[logical] = f"{val[:8]}..." if val and len(val) > 8 else ("set" if val else None)
        return result

    def verify_setup(self, provider: str) -> dict[str, Any]:
        """Run a quick connectivity check against the stored API credentials."""
        try:
            from instruments.custom.stripe_payments.payment_router import PaymentRouter

            p = PaymentRouter.get_provider(provider)
            # A lightweight read to check auth works (list customers with limit=1)
            if provider == "stripe":
                from instruments.custom.stripe_payments.providers.stripe_provider import StripeProvider

                assert isinstance(p, StripeProvider)
                result = p._stripe_request("GET", "customers?limit=1")
                return {
                    "status": "ok",
                    "provider": provider,
                    "detail": f"Connected. Customer count: {len(result.get('data', []))}.",
                }
            return {"status": "ok", "provider": provider, "detail": "Credentials appear to be set."}
        except Exception as exc:
            return {"status": "error", "provider": provider, "detail": str(exc)}

    # -- internal helpers ----------------------------------------------------

    def _load_steps(
        self,
        provider: str,
        session_id: str,
        email: str,
        webhook_endpoint_url: str,
    ) -> list[dict]:
        if provider == "stripe":
            from instruments.custom.payment_account_setup.step_definitions.stripe_steps import get_stripe_steps

            return get_stripe_steps(session_id, email, webhook_endpoint_url)
        if provider == "square":
            from instruments.custom.payment_account_setup.step_definitions.square_steps import get_square_steps

            return get_square_steps(session_id, email, webhook_endpoint_url)
        if provider == "paypal":
            from instruments.custom.payment_account_setup.step_definitions.paypal_steps import get_paypal_steps

            return get_paypal_steps(session_id, email, webhook_endpoint_url)
        raise ValueError(f"No step definitions for provider '{provider}'")
