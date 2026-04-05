from abc import ABC, abstractmethod
from typing import Any


class PaymentProvider(ABC):
    """Abstract base class for payment provider operations.

    Concrete implementations exist for Stripe, Square, and PayPal.
    All providers must implement every method so callers can treat them
    interchangeably regardless of the underlying payment platform.
    """

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the canonical provider identifier (e.g. 'stripe', 'square', 'paypal')."""
        raise NotImplementedError

    @abstractmethod
    def create_customer(self, email: str, name: str, metadata: dict[str, Any] | None = None) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_customer(self, customer_id: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def create_product(self, name: str, description: str, metadata: dict[str, Any] | None = None) -> dict:
        raise NotImplementedError

    @abstractmethod
    def create_price(
        self,
        product_id: str,
        unit_amount_cents: int,
        currency: str = "usd",
        recurring_interval: str | None = None,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def create_checkout_session(
        self,
        price_id: str,
        customer_id: str,
        mode: str = "payment",
        success_url: str = "",
        cancel_url: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def create_invoice(
        self,
        customer_id: str,
        items: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def finalize_invoice(self, invoice_id: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> dict:
        raise NotImplementedError

    @abstractmethod
    def update_subscription(self, subscription_id: str, new_price_id: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def construct_webhook_event(self, payload: str, sig_header: str, secret: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def list_payment_methods(self, customer_id: str) -> list[dict]:
        """List saved payment methods for a customer."""
        raise NotImplementedError

    @abstractmethod
    def update_customer_payment_method(self, customer_id: str, payment_method_token: str) -> dict:
        """Set or update the default payment method for a customer."""
        raise NotImplementedError

    @abstractmethod
    def retry_payment(self, payment_id: str) -> dict:
        """Attempt to collect payment on a past-due invoice or payment intent."""
        raise NotImplementedError

    @abstractmethod
    def create_billing_portal_session(self, customer_id: str, return_url: str) -> dict:
        """Create a customer-facing billing management session.

        Returns a dict with at minimum a ``url`` key pointing to the
        provider's billing portal or account management page.
        """
        raise NotImplementedError


# Backwards-compatible alias — remove once all import sites are updated.
StripePaymentProvider = PaymentProvider
