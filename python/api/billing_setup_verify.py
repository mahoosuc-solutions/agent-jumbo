from python.helpers.api import ApiHandler, Request, Response


class BillingSetupVerify(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        manager = PaymentAccountSetupManager()
        tenant_id = str(input.get("tenant_id") or "default").strip() or "default"
        provider = str(input.get("provider") or "stripe").strip().lower()
        mock = bool(input.get("mock", False))
        return manager.verify_setup(provider=provider, tenant_id=tenant_id, mock=mock)
