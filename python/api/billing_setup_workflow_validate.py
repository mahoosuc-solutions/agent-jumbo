from python.helpers.api import ApiHandler, Request, Response


class BillingSetupWorkflowValidate(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        manager = PaymentAccountSetupManager()
        run_id = str(input.get("run_id") or "").strip()
        if not run_id:
            return {"error": "run_id is required"}

        selected_slugs = input.get("selected_slugs") or []
        if not isinstance(selected_slugs, list):
            selected_slugs = [selected_slugs]

        return manager.validate_workflow(
            run_id=run_id,
            apply_catalog_sync=bool(input.get("apply_catalog_sync", False)),
            selected_slugs=[str(slug).strip() for slug in selected_slugs if str(slug).strip()],
            target_offer_slug=str(input.get("target_offer_slug") or "").strip() or None,
            checkout_completed=bool(input.get("checkout_completed", False)),
            mock=bool(input.get("mock", False)),
        )
