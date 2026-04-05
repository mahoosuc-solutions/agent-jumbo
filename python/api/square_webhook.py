"""
Square Webhook API Endpoint
Receives and verifies Square webhook events at /square_webhook.
"""

from __future__ import annotations

import json
import logging
import os

from flask import Request, Response

from python.helpers import files
from python.helpers.api import ApiHandler

logger = logging.getLogger(__name__)


class SquareWebhookEndpoint(ApiHandler):
    """Endpoint for Square webhook events at ``/square_webhook``."""

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
        """Verify Square HMAC-SHA256 signature and dispatch the event."""
        from instruments.custom.stripe_payments.square_webhook_handler import SquareWebhookHandler
        from instruments.custom.stripe_payments.stripe_db import StripePaymentDatabase

        raw_body = request.get_data(as_text=True)
        if not raw_body:
            return Response(
                json.dumps({"error": "Empty request body"}),
                status=400,
                mimetype="application/json",
            )

        signature = request.headers.get("X-Square-HMAC-SHA256-Signature", "")
        signature_key = os.environ.get("SQUARE_WEBHOOK_SIGNATURE_KEY", "")

        if not signature_key:
            logger.error("SQUARE_WEBHOOK_SIGNATURE_KEY not configured")
            return Response(
                json.dumps({"error": "Webhook signature key not configured"}),
                status=500,
                mimetype="application/json",
            )

        db_path = files.get_abs_path("./instruments/custom/stripe_payments/data/stripe_payments.db")
        db = StripePaymentDatabase(db_path)
        handler = SquareWebhookHandler(db)

        if not handler.verify_signature(raw_body, signature, signature_key):
            logger.warning("Square webhook signature verification failed")
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

        event_id = payload.get("event_id", "")
        event_type = payload.get("type", "")
        data = payload.get("data", {}).get("object", {})

        result = handler.handle_event(event_id, event_type, data)
        logger.info("Square webhook processed: %s %s -> %s", event_id, event_type, result.get("status"))
        return result
