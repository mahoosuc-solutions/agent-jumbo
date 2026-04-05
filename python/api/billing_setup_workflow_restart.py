from python.helpers.api import ApiHandler, Request, Response


class BillingSetupWorkflowRestart(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        manager = PaymentAccountSetupManager()
        run_id = str(input.get("run_id") or "").strip()
        checkpoint_id = str(input.get("checkpoint_id") or "").strip()
        if not run_id or not checkpoint_id:
            return {"error": "run_id and checkpoint_id are required"}

        mock = bool(input.get("mock", False))
        return manager.restart_workflow_from_checkpoint(run_id=run_id, checkpoint_id=checkpoint_id, mock=mock)
