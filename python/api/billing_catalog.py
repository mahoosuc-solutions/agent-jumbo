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
        if request.method == "POST":
            return manager.update_catalog_offer(
                tenant_id=str(tenant_id).strip() or "default",
                provider=str(provider).strip().lower() or "stripe",
                slug=str(input.get("slug") or "").strip(),
                active=input.get("active"),
                monthly_price_usd=input.get("monthly_price_usd"),
                setup_price_usd=input.get("setup_price_usd"),
                name=input.get("name"),
                tagline=input.get("tagline"),
                description=input.get("description"),
            )
        return manager.get_catalog(tenant_id=tenant_id, provider=provider)
