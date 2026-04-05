"""
Payment Account Setup Tool for Agent Jumbo

Guides the operator through browser-assisted account creation for Stripe,
Square, and PayPal. The agent drives each step using MCP browser tools
(Playwright / Chrome DevTools), pausing at human-required gates for the
operator to complete CAPTCHA, 2FA, email verification, or document upload.

Usage examples:
  {"action": "start_setup", "provider": "stripe", "business_name": "Acme Inc", "email": "owner@acme.com"}
  {"action": "next_step", "session_id": "stripe_abc123"}
  {"action": "confirm_human_step", "session_id": "stripe_abc123"}
  {"action": "store_credentials", "provider": "stripe", "credentials": {"stripe_secret_key": "sk_test_..."}}  # pragma: allowlist secret
  {"action": "get_session", "session_id": "stripe_abc123"}
  {"action": "list_sessions"}
  {"action": "verify_setup", "provider": "stripe"}
"""

import json

from python.helpers.tool import Response, Tool


class PaymentAccountSetup(Tool):
    def __init__(self, agent, name, method, args, message, loop_data, **kwargs):
        super().__init__(agent, name, method, args, message, loop_data, **kwargs)
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        self.manager = PaymentAccountSetupManager()

    async def execute(self, **kwargs):
        action = (self.args.get("action") or "").lower().strip()

        action_map = {
            "start_setup": self._start_setup,
            "next_step": self._next_step,
            "confirm_human_step": self._confirm_human_step,
            "store_credentials": self._store_credentials,
            "get_session": self._get_session,
            "list_sessions": self._list_sessions,
            "verify_setup": self._verify_setup,
        }

        handler = action_map.get(action)
        if not handler:
            return Response(
                message=json.dumps(
                    {
                        "error": f"Unknown action '{action}'",
                        "available_actions": list(action_map.keys()),
                    }
                ),
                break_loop=False,
            )

        try:
            result = await handler()
            return Response(message=json.dumps(result, indent=2, default=str), break_loop=False)
        except Exception as exc:
            return Response(
                message=json.dumps({"error": str(exc), "action": action}),
                break_loop=False,
            )

    # -- action handlers -----------------------------------------------------

    async def _start_setup(self):
        provider = self.args.get("provider", "stripe")
        business_name = self.args.get("business_name", "")
        email = self.args.get("email", "")
        country = self.args.get("country", "us")
        webhook_url = self.args.get("webhook_endpoint_url", "")

        if not business_name or not email:
            return {"error": "business_name and email are required"}

        result = self.manager.start_setup(
            provider=provider,
            business_name=business_name,
            email=email,
            country=country,
            webhook_endpoint_url=webhook_url,
        )
        return result

    async def _next_step(self):
        session_id = self.args.get("session_id", "")
        if not session_id:
            return {"error": "session_id is required"}

        step_result = self.args.get("step_result")
        if isinstance(step_result, str):
            try:
                step_result = json.loads(step_result)
            except (json.JSONDecodeError, TypeError):
                step_result = {"raw": step_result}

        return self.manager.advance_step(
            session_id=session_id,
            step_result=step_result,
            human_confirmed=False,
        )

    async def _confirm_human_step(self):
        session_id = self.args.get("session_id", "")
        if not session_id:
            return {"error": "session_id is required"}

        # Any manually provided values the operator entered (e.g. pasted API key)
        manual_credentials = self.args.get("credentials")
        if isinstance(manual_credentials, str):
            try:
                manual_credentials = json.loads(manual_credentials)
            except (json.JSONDecodeError, TypeError):
                manual_credentials = {}

        return self.manager.advance_step(
            session_id=session_id,
            step_result=manual_credentials or {},
            human_confirmed=True,
        )

    async def _store_credentials(self):
        provider = self.args.get("provider", "")
        credentials = self.args.get("credentials", {})
        session_id = self.args.get("session_id")
        push_to_vercel = bool(self.args.get("push_to_vercel", False))

        if not provider:
            return {"error": "provider is required"}
        if isinstance(credentials, str):
            try:
                credentials = json.loads(credentials)
            except (json.JSONDecodeError, TypeError):
                return {"error": "credentials must be a JSON object"}

        written = self.manager.store_credentials(
            provider=provider,
            credentials=credentials,
            session_id=session_id,
            push_to_vercel=push_to_vercel,
        )
        return {"status": "stored", "provider": provider, "written_keys": written}

    async def _get_session(self):
        session_id = self.args.get("session_id", "")
        if not session_id:
            return {"error": "session_id is required"}
        session = self.manager.get_session(session_id)
        if session is None:
            return {"error": f"Session '{session_id}' not found"}
        return session

    async def _list_sessions(self):
        sessions = self.manager.list_sessions()
        return {
            "count": len(sessions),
            "sessions": [
                {
                    "session_id": s["session_id"],
                    "provider": s["provider"],
                    "status": s["status"],
                    "current_step": s["current_step"],
                    "total_steps": s["total_steps"],
                    "business_name": s["business_name"],
                    "created_at": s["created_at"],
                }
                for s in sessions
            ],
        }

    async def _verify_setup(self):
        provider = self.args.get("provider", "stripe")
        return self.manager.verify_setup(provider)
