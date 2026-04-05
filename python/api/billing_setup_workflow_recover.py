from python.helpers.api import ApiHandler, Request, Response


class BillingSetupWorkflowRecover(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        manager = PaymentAccountSetupManager()
        run_id = str(input.get("run_id") or "").strip()
        if not run_id:
            return {"error": "run_id is required"}

        mock = bool(input.get("mock", False))
        return manager.recover_workflow(run_id=run_id, mock=mock)
