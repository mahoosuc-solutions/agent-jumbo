from python.helpers.api import ApiHandler, Request, Response


class BillingSetupWorkflowStatus(ApiHandler):
    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        manager = PaymentAccountSetupManager()
        run_id = str(input.get("run_id") or request.args.get("run_id") or "").strip() or None
        tenant_id = str(input.get("tenant_id") or request.args.get("tenant_id") or "default").strip() or "default"
        provider = str(input.get("provider") or request.args.get("provider") or "stripe").strip().lower()
        mock = str(input.get("mock") or request.args.get("mock") or "").lower() in {"1", "true", "yes"}
        return manager.get_workflow_status(run_id=run_id, tenant_id=tenant_id, provider=provider, mock=mock)
