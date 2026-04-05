from python.helpers.api import ApiHandler, Request, Response


class BillingSetupWorkflowCheckpoints(ApiHandler):
    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        manager = PaymentAccountSetupManager()
        run_id = str(input.get("run_id") or request.args.get("run_id") or "").strip()
        if not run_id:
            return {"error": "run_id is required"}

        run = manager.db.get_workflow_run(run_id)
        if run is None:
            return {"error": f"Workflow run '{run_id}' not found"}

        return {
            "run_id": run_id,
            "provider": run["provider"],
            "tenant_id": run["tenant_id"],
            "checkpoints": manager.list_workflow_checkpoints(run_id),
        }
