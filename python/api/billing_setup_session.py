from python.helpers.api import ApiHandler, Request, Response


class BillingSetupSession(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        manager = PaymentAccountSetupManager()
        provider = str(input.get("provider") or "stripe").strip().lower()
        business_name = str(input.get("business_name") or "").strip()
        email = str(input.get("email") or "").strip()
        country = str(input.get("country") or "us").strip()
        tenant_id = str(input.get("tenant_id") or "default").strip() or "default"
        webhook_endpoint_url = str(input.get("webhook_endpoint_url") or "").strip()

        if not business_name or not email:
            return {"error": "business_name and email are required"}

        return manager.start_setup(
            provider=provider,
            business_name=business_name,
            email=email,
            country=country,
            webhook_endpoint_url=webhook_endpoint_url,
            tenant_id=tenant_id,
        )
