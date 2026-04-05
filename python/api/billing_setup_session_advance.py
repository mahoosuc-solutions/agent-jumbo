from python.helpers.api import ApiHandler, Request, Response


class BillingSetupSessionAdvance(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        manager = PaymentAccountSetupManager()
        session_id = str(input.get("session_id") or "").strip()
        if not session_id:
            return {"error": "session_id is required"}

        step_result = input.get("step_result") or {}
        human_confirmed = bool(input.get("human_confirmed", False))
        return manager.advance_step(session_id=session_id, step_result=step_result, human_confirmed=human_confirmed)
