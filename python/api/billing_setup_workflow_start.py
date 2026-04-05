from python.helpers.api import ApiHandler, Request, Response


class BillingSetupWorkflowStart(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        manager = PaymentAccountSetupManager()
        provider = str(input.get("provider") or "stripe").strip().lower()
        business_name = str(input.get("business_name") or "").strip()
        email = str(input.get("email") or "").strip()
        country = str(input.get("country") or "us").strip()
        tenant_id = str(input.get("tenant_id") or "default").strip() or "default"
        webhook_endpoint_url = str(input.get("webhook_endpoint_url") or "").strip()
        target_offer_slug = str(input.get("target_offer_slug") or "").strip()
        selected_slugs = input.get("selected_slugs") or []
        if not isinstance(selected_slugs, list):
            selected_slugs = [selected_slugs]

        if not business_name or not email:
            return {"error": "business_name and email are required"}

        return manager.start_workflow(
            provider=provider,
            business_name=business_name,
            email=email,
            country=country,
            webhook_endpoint_url=webhook_endpoint_url,
            tenant_id=tenant_id,
            target_offer_slug=target_offer_slug,
            selected_slugs=[str(slug).strip() for slug in selected_slugs if str(slug).strip()],
        )
