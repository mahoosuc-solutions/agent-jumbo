from abc import ABC, abstractmethod
from typing import Any


class StripePaymentProvider(ABC):
    """Abstract base class for Stripe payment operations."""

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
