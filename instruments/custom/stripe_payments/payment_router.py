"""
Payment Router — factory that resolves the correct PaymentProvider implementation
based on a provider name string.

Usage::

    from instruments.custom.stripe_payments.payment_router import PaymentRouter

    provider = PaymentRouter.get_provider("stripe")          # real Stripe
    mock_sq  = PaymentRouter.get_provider("square", mock=True)  # mock Square
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from instruments.custom.stripe_payments.providers.base import PaymentProvider


class PaymentRouter:
    """Factory for payment provider instances."""

    @staticmethod
    def get_provider(provider: str = "stripe", mock: bool = False) -> PaymentProvider:
        """Return a concrete PaymentProvider for the given provider name.

        Args:
            provider: One of ``"stripe"``, ``"square"``, ``"paypal"``.
            mock: If True, return the deterministic mock variant.

        Raises:
            ValueError: If *provider* is not recognised.
        """
        provider = provider.lower().strip()

        if provider == "stripe":
            if mock:
                from instruments.custom.stripe_payments.providers.mock_provider import MockStripeProvider

                return MockStripeProvider()
            from instruments.custom.stripe_payments.providers.stripe_provider import StripeProvider

            return StripeProvider()

        if provider == "square":
            if mock:
                from instruments.custom.stripe_payments.providers.mock_square_provider import MockSquareProvider

                return MockSquareProvider()
            from instruments.custom.stripe_payments.providers.square_provider import SquareProvider

            return SquareProvider()

        if provider == "paypal":
            if mock:
                from instruments.custom.stripe_payments.providers.mock_paypal_provider import MockPayPalProvider

                return MockPayPalProvider()
            from instruments.custom.stripe_payments.providers.paypal_provider import PayPalProvider

            return PayPalProvider()

        raise ValueError(f"Unknown payment provider '{provider}'. Supported providers: 'stripe', 'square', 'paypal'.")

    @staticmethod
    def get_customer_provider(customer_id: int | str, db) -> PaymentProvider:
        """Return the provider instance for an existing customer's stored provider field.

        Falls back to Stripe if no ``payment_provider`` column is present.
        """
        customer = db.get_customer(customer_id=customer_id)
        if customer is None:
            raise ValueError(f"Customer {customer_id!r} not found in local database")
        provider_name = customer.get("payment_provider", "stripe") or "stripe"
        return PaymentRouter.get_provider(provider_name)
