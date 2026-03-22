"""
Stripe Webhook API Endpoint
Receives and verifies Stripe webhook events, then dispatches them
to the StripeWebhookHandler for processing.

This is a direct API handler (not using WebhookRouter) since Stripe
webhooks require raw body access for signature verification.
"""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING

from flask import Flask, Request, Response

if TYPE_CHECKING:
    import threading

from python.helpers import files
from python.helpers.api import ApiHandler

logger = logging.getLogger(__name__)


class StripeWebhookEndpoint(ApiHandler):
    """Direct endpoint for Stripe webhook events at ``/api/stripe/webhook``."""

    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def requires_api_key(cls) -> bool:
        return False

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        """Verify Stripe signature and dispatch the event.

        1. Read raw body for signature verification.
        2. Verify signature using provider.construct_webhook_event().
        3. Dispatch to webhook_handler.handle_event().
        4. Return 200 with result.
        """
        from instruments.custom.stripe_payments.stripe_manager import StripePaymentManager
        from instruments.custom.stripe_payments.webhook_handler import StripeWebhookHandler

        # Read raw body — must use request.get_data() before JSON parsing
        raw_body = request.get_data(as_text=True)
        if not raw_body:
            return Response(
                json.dumps({"error": "Empty request body"}),
                status=400,
                mimetype="application/json",
            )

        # Get Stripe signature header
        sig_header = request.headers.get("Stripe-Signature", "")

        # Get webhook secret from environment or settings
        webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
        if not webhook_secret:
            try:
                from python.helpers import settings as settings_helper

                config = settings_helper.get_settings()
                webhook_secret = config.get("stripe_webhook_secret", "")
            except Exception:
                pass

        if not webhook_secret:
            logger.error("STRIPE_WEBHOOK_SECRET not configured")
            return Response(
                json.dumps({"error": "Webhook secret not configured"}),
                status=500,
                mimetype="application/json",
            )

        # Verify signature using the real provider
        try:
            from instruments.custom.stripe_payments.providers.stripe_provider import (
                StripePaymentProvider as RealProvider,
            )

            provider = RealProvider()
            event = provider.construct_webhook_event(raw_body, sig_header, webhook_secret)
        except ValueError as exc:
            logger.warning("Stripe webhook signature verification failed: %s", exc)
            return Response(
                json.dumps({"error": "Invalid signature", "detail": str(exc)}),
                status=401,
                mimetype="application/json",
            )
        except Exception as exc:
            logger.error("Stripe webhook verification error: %s", exc)
            return Response(
                json.dumps({"error": "Verification failed"}),
                status=400,
                mimetype="application/json",
            )

        # Extract event fields
        event_id = event.get("id", "")
        event_type = event.get("type", "")
        data_object = event.get("data", {}).get("object", {})

        if not event_id or not event_type:
            return Response(
                json.dumps({"error": "Missing event id or type"}),
                status=400,
                mimetype="application/json",
            )

        # Initialize manager and handler
        db_path = files.get_abs_path("./instruments/custom/stripe_payments/data/stripe_payments.db")
        manager = StripePaymentManager(db_path)
        handler = StripeWebhookHandler(manager)

        # Dispatch
        result = handler.handle_event(event_id, event_type, data_object)

        logger.info("Stripe webhook processed: %s %s -> %s", event_id, event_type, result.get("status"))

        return result


def register_routes(app: Flask, thread_lock: threading.Lock) -> None:
    """Register the ``/api/stripe/webhook`` route with a Flask app."""
    import asyncio

    handler = StripeWebhookEndpoint(app, thread_lock)

    def stripe_webhook_view():
        from flask import request

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(handler.handle_request(request))
        finally:
            loop.close()

    app.add_url_rule(
        "/api/stripe/webhook",
        endpoint="stripe_webhook",
        view_func=stripe_webhook_view,
        methods=StripeWebhookEndpoint.get_methods(),
    )
