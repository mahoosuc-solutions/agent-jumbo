from python.helpers.api import ApiHandler, Request, Response


class BillingSetupWorkflowAdvance(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        manager = PaymentAccountSetupManager()
        run_id = str(input.get("run_id") or "").strip()
        if not run_id:
            return {"error": "run_id is required"}

        step_result = input.get("step_result") or {}
        human_confirmed = bool(input.get("human_confirmed", False))
        mock = bool(input.get("mock", False))
        return manager.advance_workflow(
            run_id=run_id,
            step_result=step_result,
            human_confirmed=human_confirmed,
            mock=mock,
        )
