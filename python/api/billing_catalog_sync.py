from python.helpers.api import ApiHandler, Request, Response


class BillingCatalogSync(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        manager = PaymentAccountSetupManager()
        tenant_id = str(input.get("tenant_id") or "default").strip() or "default"
        provider = str(input.get("provider") or "stripe").strip().lower()
        selected_slugs = input.get("selected_slugs") or []
        if not isinstance(selected_slugs, list):
            selected_slugs = [selected_slugs]
        return manager.sync_catalog(
            tenant_id=tenant_id,
            provider=provider,
            apply=bool(input.get("apply", False)),
            selected_slugs=[str(slug) for slug in selected_slugs if str(slug).strip()],
            mock=bool(input.get("mock", False)),
        )
