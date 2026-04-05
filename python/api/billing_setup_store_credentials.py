from python.helpers.api import ApiHandler, Request, Response


class BillingSetupStoreCredentials(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager

        manager = PaymentAccountSetupManager()
        provider = str(input.get("provider") or "stripe").strip().lower()
        tenant_id = str(input.get("tenant_id") or "default").strip() or "default"
        credentials = input.get("credentials") or {}
        session_id = input.get("session_id")

        if not isinstance(credentials, dict):
            return {"error": "credentials must be an object"}

        written = manager.store_credentials(
            provider=provider,
            credentials=credentials,
            session_id=session_id,
            tenant_id=tenant_id,
            write_to_env=bool(input.get("write_to_env", False)),
            push_to_vercel=bool(input.get("push_to_vercel", False)),
        )
        return {"status": "stored", "provider": provider, "written_keys": written}
