"""Billing portal API endpoints.

Provides session-authenticated billing management for customers:
- GET  /billing/summary     — current subscription, invoices, payment method info
- POST /billing/portal      — create a provider billing portal session (returns URL)
- POST /billing/cancel      — cancel subscription at period end
- POST /billing/upgrade     — change subscription plan

All endpoints require a valid session cookie (Flask session with customer identity).
The customer's payment provider is determined from the local StripePaymentDatabase.
"""

import logging

from flask import Blueprint, jsonify, request, session

from instruments.custom.stripe_payments.payment_router import PaymentRouter
from instruments.custom.stripe_payments.stripe_manager import StripePaymentManager
from python.helpers.files import get_abs_path

logger = logging.getLogger(__name__)

billing_bp = Blueprint("billing", __name__, url_prefix="/billing")

_DB_PATH = get_abs_path("./instruments/custom/stripe_payments/data/stripe_payments.db")


def _get_manager() -> StripePaymentManager:
    return StripePaymentManager(_DB_PATH)


def _get_customer_from_session() -> dict | None:
    """Resolve the current session user to a local customer record."""
    manager = _get_manager()
    # Try email from session first, then fallback to session user_id
    email = session.get("user_email") or session.get("email")
    if email:
        return manager.get_customer(email=email)
    return None


@billing_bp.get("/summary")
def billing_summary():
    """Return current subscription, invoice history, and payment method summary."""
    customer = _get_customer_from_session()
    if customer is None:
        return jsonify({"error": "Not authenticated or customer not found"}), 401

    manager = _get_manager()
    stripe_customer_id = customer.get("stripe_customer_id", "")
    provider_name = customer.get("payment_provider", "stripe") or "stripe"

    subscriptions = manager.list_subscriptions(stripe_customer_id)
    invoices = manager.list_invoices(stripe_customer_id)

    # Get active subscription details
    active_sub = next(
        (s for s in subscriptions if s.get("status") in ("active", "trialing")),
        None,
    )

    # Get recent invoices (last 10)
    recent_invoices = sorted(invoices, key=lambda i: i.get("created_at", ""), reverse=True)[:10]

    # Payment method summary — use mock-safe approach
    payment_methods = []
    try:
        provider = PaymentRouter.get_provider(provider_name)
        if stripe_customer_id:
            payment_methods = provider.list_payment_methods(stripe_customer_id)
    except Exception as exc:
        logger.warning("Could not fetch payment methods: %s", exc)

    return jsonify(
        {
            "customer": {
                "id": customer.get("id"),
                "email": customer.get("email"),
                "name": customer.get("name"),
                "provider": provider_name,
            },
            "subscription": active_sub,
            "all_subscriptions": subscriptions,
            "recent_invoices": recent_invoices,
            "payment_methods": payment_methods[:3],  # cap for summary view
            "has_active_subscription": active_sub is not None,
        }
    )


@billing_bp.post("/portal")
def billing_portal():
    """Create a provider billing portal session and return its URL."""
    customer = _get_customer_from_session()
    if customer is None:
        return jsonify({"error": "Not authenticated or customer not found"}), 401

    data = request.get_json(silent=True) or {}
    return_url = data.get("return_url") or request.host_url.rstrip("/") + "/billing"

    stripe_customer_id = customer.get("stripe_customer_id", "")
    provider_name = customer.get("payment_provider", "stripe") or "stripe"

    try:
        provider = PaymentRouter.get_provider(provider_name)
        result = provider.create_billing_portal_session(stripe_customer_id, return_url)
        return jsonify({"portal_url": result.get("url", ""), "provider": provider_name})
    except Exception as exc:
        logger.error("billing_portal error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@billing_bp.post("/cancel")
def billing_cancel():
    """Cancel the active subscription at the end of the current billing period."""
    customer = _get_customer_from_session()
    if customer is None:
        return jsonify({"error": "Not authenticated or customer not found"}), 401

    manager = _get_manager()
    stripe_customer_id = customer.get("stripe_customer_id", "")
    subscriptions = manager.list_subscriptions(stripe_customer_id)
    active_sub = next(
        (s for s in subscriptions if s.get("status") in ("active", "trialing")),
        None,
    )

    if not active_sub:
        return jsonify({"error": "No active subscription found"}), 404

    subscription_id = active_sub.get("stripe_subscription_id", "")
    try:
        result = manager.cancel_subscription(subscription_id, at_period_end=True)
        return jsonify(
            {
                "status": "cancellation_scheduled",
                "subscription_id": subscription_id,
                "effective_date": active_sub.get("current_period_end"),
                "result": result,
            }
        )
    except Exception as exc:
        logger.error("billing_cancel error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@billing_bp.post("/upgrade")
def billing_upgrade():
    """Upgrade or downgrade the active subscription to a new price."""
    customer = _get_customer_from_session()
    if customer is None:
        return jsonify({"error": "Not authenticated or customer not found"}), 401

    data = request.get_json(silent=True) or {}
    new_price_id = data.get("price_id", "")
    if not new_price_id:
        return jsonify({"error": "price_id is required"}), 400

    manager = _get_manager()
    stripe_customer_id = customer.get("stripe_customer_id", "")
    subscriptions = manager.list_subscriptions(stripe_customer_id)
    active_sub = next(
        (s for s in subscriptions if s.get("status") in ("active", "trialing")),
        None,
    )

    if not active_sub:
        return jsonify({"error": "No active subscription found"}), 404

    subscription_id = active_sub.get("stripe_subscription_id", "")
    try:
        result = manager.update_subscription(subscription_id, new_price_id)
        return jsonify(
            {
                "status": "updated",
                "subscription_id": subscription_id,
                "new_price_id": new_price_id,
                "result": result,
            }
        )
    except Exception as exc:
        logger.error("billing_upgrade error: %s", exc)
        return jsonify({"error": str(exc)}), 500
