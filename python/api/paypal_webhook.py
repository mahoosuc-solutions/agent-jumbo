"""
PayPal Webhook API Endpoint
Receives and verifies PayPal webhook events at /paypal_webhook.
"""

from __future__ import annotations

import json
import logging
import os

from flask import Request, Response

from python.helpers import files
from python.helpers.api import ApiHandler

logger = logging.getLogger(__name__)


class PayPalWebhookEndpoint(ApiHandler):
    """Endpoint for PayPal webhook events at ``/paypal_webhook``."""

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
        """Verify PayPal webhook signature via PayPal API and dispatch the event."""
        from instruments.custom.stripe_payments.paypal_webhook_handler import PayPalWebhookHandler
        from instruments.custom.stripe_payments.stripe_db import StripePaymentDatabase

        raw_body = request.get_data(as_text=True)
        if not raw_body:
            return Response(
                json.dumps({"error": "Empty request body"}),
                status=400,
                mimetype="application/json",
            )

        webhook_id = os.environ.get("PAYPAL_WEBHOOK_ID", "")
        if not webhook_id:
            logger.error("PAYPAL_WEBHOOK_ID not configured")
            return Response(
                json.dumps({"error": "Webhook ID not configured"}),
                status=500,
                mimetype="application/json",
            )

        db_path = files.get_abs_path("./instruments/custom/stripe_payments/data/stripe_payments.db")
        db = StripePaymentDatabase(db_path)
        handler = PayPalWebhookHandler(db)

        # Build verification context from headers
        headers = {
            "PAYPAL-AUTH-ALGO": request.headers.get("PAYPAL-AUTH-ALGO", ""),
            "PAYPAL-CERT-URL": request.headers.get("PAYPAL-CERT-URL", ""),
            "PAYPAL-TRANSMISSION-ID": request.headers.get("PAYPAL-TRANSMISSION-ID", ""),
            "PAYPAL-TRANSMISSION-SIG": request.headers.get("PAYPAL-TRANSMISSION-SIG", ""),
            "PAYPAL-TRANSMISSION-TIME": request.headers.get("PAYPAL-TRANSMISSION-TIME", ""),
        }

        client_id = os.environ.get("PAYPAL_CLIENT_ID", "")
        client_secret = os.environ.get("PAYPAL_CLIENT_SECRET", "")
        environment = os.environ.get("PAYPAL_ENVIRONMENT", "sandbox")

        if not handler.verify_signature(raw_body, headers, webhook_id, client_id, client_secret, environment):
            logger.warning("PayPal webhook signature verification failed")
            return Response(
                json.dumps({"error": "Invalid signature"}),
                status=401,
                mimetype="application/json",
            )

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            return Response(
                json.dumps({"error": f"Invalid JSON: {exc}"}),
                status=400,
                mimetype="application/json",
            )

        event_id = payload.get("id", "")
        event_type = payload.get("event_type", "")
        resource = payload.get("resource", {})

        result = handler.handle_event(event_id, event_type, resource)
        logger.info("PayPal webhook processed: %s %s -> %s", event_id, event_type, result.get("status"))
        return result
