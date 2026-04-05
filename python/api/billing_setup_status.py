from python.helpers.api import ApiHandler, Request, Response


class BillingSetupStatus(ApiHandler):
    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        manager = PaymentAccountSetupManager()
        tenant_id = input.get("tenant_id") or request.args.get("tenant_id") or "default"
        provider = input.get("provider") or request.args.get("provider") or "stripe"
        mock = str(input.get("mock") or request.args.get("mock") or "").lower() in {"1", "true", "yes"}
        include_catalog = str(input.get("include_catalog") or request.args.get("include_catalog") or "").lower() in {
            "1",
            "true",
            "yes",
        }
        return manager.get_status(tenant_id=tenant_id, provider=provider, include_catalog=include_catalog, mock=mock)
