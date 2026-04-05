from python.helpers.api import ApiHandler, Request, Response


class BillingCatalog(ApiHandler):
    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        manager = PaymentAccountSetupManager()
        tenant_id = input.get("tenant_id") or request.args.get("tenant_id") or "default"
        provider = input.get("provider") or request.args.get("provider") or "stripe"
        return manager.get_catalog(tenant_id=tenant_id, provider=provider)
