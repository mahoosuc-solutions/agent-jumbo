"""
Stripe Payment Manager
Core business logic for Stripe integration: customers, products, invoicing,
subscriptions, and cross-system sync with Portfolio Manager and Customer Lifecycle.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

from instruments.custom.stripe_payments.stripe_db import StripePaymentDatabase
from python.helpers.files import get_abs_path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class StripePaymentManager:
    """Orchestrates Stripe payment operations with local persistence and
    cross-system synchronisation (Portfolio Manager, Customer Lifecycle).
    """

    def __init__(self, db_path: str):
        self.db = StripePaymentDatabase(db_path)

    # ------------------------------------------------------------------
    # Provider helpers
    # ------------------------------------------------------------------

    def _get_provider(self, mock: bool = False):
        """Return a mock or real Stripe provider instance."""
        if mock:
            from instruments.custom.stripe_payments.providers.mock_provider import MockStripeProvider

            return MockStripeProvider()

        from instruments.custom.stripe_payments.providers.stripe_provider import StripePaymentProvider

        return StripePaymentProvider()

    # ------------------------------------------------------------------
    # Phase 1 — Customers
    # ------------------------------------------------------------------

    def create_customer(
        self,
        email: str,
        name: str,
        metadata: dict[str, Any] | None = None,
        mock: bool = False,
    ) -> dict[str, Any]:
        """Create a customer in Stripe and store locally."""
        provider = self._get_provider(mock)
        result = provider.create_customer(email, name, metadata)
        local_id = self.db.add_customer(
            stripe_customer_id=result["id"],
            email=email,
            name=name,
            metadata=metadata,
        )
        return {**result, "local_id": local_id}

    def get_customer(
        self,
        customer_id: int | None = None,
        email: str | None = None,
    ) -> dict[str, Any] | None:
        """Look up a customer from local DB by ID or email."""
        return self.db.get_customer(customer_id=customer_id, email=email)

    def list_customers(self) -> list[dict[str, Any]]:
        """List all locally-stored customers."""
        return self.db.list_customers()

    # ------------------------------------------------------------------
    # Phase 1 — Products & Prices
    # ------------------------------------------------------------------

    def create_product(
        self,
        name: str,
        description: str,
        metadata: dict[str, Any] | None = None,
        mock: bool = False,
    ) -> dict[str, Any]:
        """Create a product in Stripe and store locally."""
        provider = self._get_provider(mock)
        result = provider.create_product(name, description, metadata)
        local_id = self.db.add_product(
            stripe_product_id=result["id"],
            name=name,
            description=description,
            metadata=metadata,
        )
        return {**result, "local_id": local_id}

    def create_price(
        self,
        stripe_product_id: str,
        amount_cents: int,
        currency: str = "usd",
        recurring_interval: str | None = None,
        mock: bool = False,
    ) -> dict[str, Any]:
        """Create a Stripe Price for an existing product and update local record."""
        provider = self._get_provider(mock)
        result = provider.create_price(stripe_product_id, amount_cents, currency, recurring_interval)

        # Update the local product record with the new price info
        local_product = self.db.get_product(stripe_product_id=stripe_product_id)
        if local_product:
            self.db.update_product(
                local_product["id"],
                stripe_price_id=result["id"],
                amount_cents=amount_cents,
                currency=currency,
                price_model="subscription" if recurring_interval else "one-time",
                recurring_interval=recurring_interval,
            )

        return result

    def get_product(
        self,
        product_id: int | None = None,
        stripe_product_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Look up a product from local DB."""
        return self.db.get_product(product_id=product_id, stripe_product_id=stripe_product_id)

    def list_products(self) -> list[dict[str, Any]]:
        """List all locally-stored products."""
        return self.db.list_products()

    # ------------------------------------------------------------------
    # Phase 2 — Portfolio product sync
    # ------------------------------------------------------------------

    def _get_portfolio_db_path(self) -> str:
        return get_abs_path("instruments", "custom", "portfolio_manager", "data", "portfolio.db")

    def _read_portfolio_product(self, portfolio_product_id: int) -> dict | None:
        """Read a product from the portfolio database."""
        db_path = self._get_portfolio_db_path()
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                """
                SELECT p.*, pr.name as project_name
                FROM products p
                JOIN projects pr ON p.project_id = pr.id
                WHERE p.id = ?
                """,
                (portfolio_product_id,),
            )
            row = cur.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as exc:
            logger.error("Failed to read portfolio product %d: %s", portfolio_product_id, exc)
            return None

    def _list_portfolio_listed_products(self) -> list[dict]:
        """List all portfolio products whose parent project is 'listed'."""
        db_path = self._get_portfolio_db_path()
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                """
                SELECT p.*, pr.name as project_name
                FROM products p
                JOIN projects pr ON p.project_id = pr.id
                WHERE pr.status = 'listed'
                """,
            )
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
        except Exception as exc:
            logger.error("Failed to list portfolio products: %s", exc)
            return []

    def sync_product_from_portfolio(
        self,
        portfolio_product_id: int,
        mock: bool = False,
    ) -> dict[str, Any]:
        """Sync a single portfolio product into Stripe.

        1. Read from portfolio DB
        2. Check if already synced (by portfolio_product_id)
        3. Create/update Stripe Product + Price
        4. Store cross-reference
        """
        existing = self.db.get_product_by_portfolio_id(portfolio_product_id)
        if existing:
            return {
                "status": "already_synced",
                "local_id": existing["id"],
                "stripe_product_id": existing["stripe_product_id"],
            }

        portfolio = self._read_portfolio_product(portfolio_product_id)
        if portfolio is None:
            return {"status": "error", "message": f"Portfolio product {portfolio_product_id} not found"}

        provider = self._get_provider(mock)

        # Create the Stripe product
        stripe_product = provider.create_product(
            name=portfolio["name"],
            description=portfolio.get("description") or portfolio.get("tagline") or "",
            metadata={"portfolio_product_id": str(portfolio_product_id)},
        )

        # Determine pricing
        amount_cents = int((portfolio.get("price") or 0) * 100)
        price_model = portfolio.get("price_model", "one-time")
        recurring_interval = "month" if price_model == "subscription" else None

        stripe_price = None
        if amount_cents > 0:
            stripe_price = provider.create_price(
                stripe_product["id"],
                amount_cents,
                "usd",
                recurring_interval,
            )

        local_id = self.db.add_product(
            stripe_product_id=stripe_product["id"],
            name=portfolio["name"],
            description=portfolio.get("description") or "",
            stripe_price_id=stripe_price["id"] if stripe_price else None,
            amount_cents=amount_cents,
            currency="usd",
            price_model=price_model,
            recurring_interval=recurring_interval,
            portfolio_product_id=portfolio_product_id,
            metadata={"portfolio_product_id": portfolio_product_id},
        )

        return {
            "status": "synced",
            "local_id": local_id,
            "stripe_product_id": stripe_product["id"],
            "stripe_price_id": stripe_price["id"] if stripe_price else None,
        }

    def sync_all_listed_products(self, mock: bool = False) -> list[dict[str, Any]]:
        """Batch sync all listed portfolio products into Stripe."""
        products = self._list_portfolio_listed_products()
        results = []
        for product in products:
            result = self.sync_product_from_portfolio(product["id"], mock=mock)
            result["portfolio_product_name"] = product["name"]
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Phase 3 — Customer sync from lifecycle + invoicing
    # ------------------------------------------------------------------

    def _get_lifecycle_db_path(self) -> str:
        return get_abs_path("instruments", "custom", "customer_lifecycle", "data", "customer_lifecycle.db")

    def _read_lifecycle_customer(self, lifecycle_customer_id: int) -> dict | None:
        """Read a customer from the lifecycle database."""
        db_path = self._get_lifecycle_db_path()
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM customers WHERE customer_id = ?",
                (lifecycle_customer_id,),
            )
            row = cur.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as exc:
            logger.error("Failed to read lifecycle customer %d: %s", lifecycle_customer_id, exc)
            return None

    def _read_lifecycle_proposal(self, proposal_id: int) -> dict | None:
        """Read a proposal from the lifecycle database."""
        db_path = self._get_lifecycle_db_path()
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM proposals WHERE proposal_id = ?",
                (proposal_id,),
            )
            row = cur.fetchone()
            conn.close()
            if row is None:
                return None
            result = dict(row)
            # Parse JSON fields
            if result.get("deliverables") and isinstance(result["deliverables"], str):
                try:
                    result["deliverables"] = json.loads(result["deliverables"])
                except (json.JSONDecodeError, TypeError):
                    pass
            return result
        except Exception as exc:
            logger.error("Failed to read lifecycle proposal %d: %s", proposal_id, exc)
            return None

    def sync_customer_from_lifecycle(
        self,
        lifecycle_customer_id: int,
        mock: bool = False,
    ) -> dict[str, Any]:
        """Sync a lifecycle customer into Stripe.

        1. Read from lifecycle DB
        2. Create Stripe customer
        3. Store cross-reference
        """
        existing = self.db.get_customer_by_lifecycle_id(lifecycle_customer_id)
        if existing:
            return {
                "status": "already_synced",
                "local_id": existing["id"],
                "stripe_customer_id": existing["stripe_customer_id"],
            }

        lifecycle = self._read_lifecycle_customer(lifecycle_customer_id)
        if lifecycle is None:
            return {"status": "error", "message": f"Lifecycle customer {lifecycle_customer_id} not found"}

        provider = self._get_provider(mock)
        email = lifecycle.get("email") or f"customer-{lifecycle_customer_id}@placeholder.local"
        name = lifecycle.get("name", "Unknown")

        stripe_customer = provider.create_customer(
            email=email,
            name=name,
            metadata={
                "lifecycle_customer_id": str(lifecycle_customer_id),
                "company": lifecycle.get("company") or "",
            },
        )

        local_id = self.db.add_customer(
            stripe_customer_id=stripe_customer["id"],
            email=email,
            name=name,
            lifecycle_customer_id=lifecycle_customer_id,
        )

        return {
            "status": "synced",
            "local_id": local_id,
            "stripe_customer_id": stripe_customer["id"],
        }

    def create_invoice_from_proposal(
        self,
        proposal_id: int,
        lifecycle_customer_id: int,
        mock: bool = False,
    ) -> dict[str, Any]:
        """Create a Stripe invoice from a lifecycle proposal.

        1. Read proposal from lifecycle DB
        2. Sync customer if needed
        3. Create Stripe invoice with line items
        4. Finalize and return invoice URL
        """
        proposal = self._read_lifecycle_proposal(proposal_id)
        if proposal is None:
            return {"status": "error", "message": f"Proposal {proposal_id} not found"}

        # Ensure customer is synced
        customer_sync = self.sync_customer_from_lifecycle(lifecycle_customer_id, mock=mock)
        stripe_customer_id = customer_sync.get("stripe_customer_id")
        if not stripe_customer_id:
            return {"status": "error", "message": "Failed to sync customer to Stripe"}

        # Build line items from proposal
        items: list[dict[str, Any]] = []
        total_cost = proposal.get("total_cost") or 0
        deliverables = proposal.get("deliverables")

        if isinstance(deliverables, list) and deliverables:
            per_item = int(total_cost * 100 / len(deliverables)) if total_cost else 0
            for deliverable in deliverables:
                desc = deliverable if isinstance(deliverable, str) else str(deliverable)
                items.append(
                    {
                        "amount": per_item,
                        "currency": "usd",
                        "description": desc,
                    }
                )
        else:
            # Single line item for the full amount
            items.append(
                {
                    "amount": int(total_cost * 100),
                    "currency": "usd",
                    "description": proposal.get("title", "Project services"),
                }
            )

        provider = self._get_provider(mock)

        invoice = provider.create_invoice(
            customer_id=stripe_customer_id,
            items=items,
            metadata={
                "proposal_id": str(proposal_id),
                "proposal_number": proposal.get("proposal_number", ""),
            },
        )

        # Finalize
        finalized = provider.finalize_invoice(invoice["id"])

        # Store locally
        self.db.add_invoice(
            stripe_invoice_id=invoice["id"],
            stripe_customer_id=stripe_customer_id,
            status=finalized.get("status", "open"),
            amount_due=finalized.get("amount_due", int(total_cost * 100)),
            currency="usd",
            hosted_url=finalized.get("hosted_invoice_url"),
            pdf_url=finalized.get("invoice_pdf"),
            proposal_id=proposal_id,
        )

        return {
            "status": "created",
            "stripe_invoice_id": invoice["id"],
            "invoice_status": finalized.get("status", "open"),
            "hosted_url": finalized.get("hosted_invoice_url"),
            "pdf_url": finalized.get("invoice_pdf"),
            "amount_due": finalized.get("amount_due", int(total_cost * 100)),
        }

    # ------------------------------------------------------------------
    # Phase 4 — Checkout
    # ------------------------------------------------------------------

    def create_checkout_for_product(
        self,
        portfolio_product_id: int,
        customer_email: str,
        mock: bool = False,
    ) -> dict[str, Any]:
        """Create a Stripe Checkout session for a portfolio product.

        Syncs the product if needed, creates/finds the customer, then
        generates a Checkout URL.
        """
        # Ensure product is synced
        product_sync = self.sync_product_from_portfolio(portfolio_product_id, mock=mock)
        stripe_product_id = product_sync.get("stripe_product_id")
        if not stripe_product_id:
            return {"status": "error", "message": "Failed to sync product to Stripe"}

        local_product = self.db.get_product(stripe_product_id=stripe_product_id)
        stripe_price_id = local_product.get("stripe_price_id") if local_product else None
        if not stripe_price_id:
            return {"status": "error", "message": "Product has no price configured"}

        # Find or create customer
        local_customer = self.db.get_customer(email=customer_email)
        if local_customer:
            stripe_customer_id = local_customer["stripe_customer_id"]
        else:
            cust_result = self.create_customer(customer_email, customer_email, mock=mock)
            stripe_customer_id = cust_result["id"]

        price_model = local_product.get("price_model", "one-time") if local_product else "one-time"
        mode = "subscription" if price_model == "subscription" else "payment"

        provider = self._get_provider(mock)
        session = provider.create_checkout_session(
            price_id=stripe_price_id,
            customer_id=stripe_customer_id,
            mode=mode,
            metadata={"portfolio_product_id": str(portfolio_product_id)},
        )

        return {
            "status": "created",
            "checkout_url": session.get("url"),
            "session_id": session["id"],
            "mode": mode,
        }

    # ------------------------------------------------------------------
    # Phase 5 — Subscriptions
    # ------------------------------------------------------------------

    def create_subscription(
        self,
        stripe_customer_id: str,
        stripe_price_id: str,
        trial_days: int = 0,
        mock: bool = False,
    ) -> dict[str, Any]:
        """Create a subscription in Stripe and store locally."""
        provider = self._get_provider(mock)
        result = provider.create_subscription(
            customer_id=stripe_customer_id,
            price_id=stripe_price_id,
            trial_days=trial_days if trial_days > 0 else None,
        )

        # Determine amount from local prices
        products = self.db.list_products()
        amount_cents = 0
        recurring_interval = "month"
        for p in products:
            if p.get("stripe_price_id") == stripe_price_id:
                amount_cents = p.get("amount_cents") or 0
                recurring_interval = p.get("recurring_interval") or "month"
                break

        self.db.add_subscription(
            stripe_subscription_id=result["id"],
            stripe_customer_id=stripe_customer_id,
            stripe_price_id=stripe_price_id,
            status=result.get("status", "active"),
            current_period_start=result.get("current_period_start"),
            current_period_end=result.get("current_period_end"),
            amount_cents=amount_cents,
            currency="usd",
            recurring_interval=recurring_interval,
        )

        return result

    def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True,
    ) -> dict[str, Any]:
        """Cancel a subscription. By default cancels at period end."""
        # Determine mock from stored sub — always use real if we have a real sub ID
        mock = subscription_id.startswith("sub_mock_")
        provider = self._get_provider(mock)
        result = provider.cancel_subscription(subscription_id, at_period_end)

        self.db.update_subscription(
            subscription_id,
            status=result.get("status", "canceled"),
            cancel_at_period_end=1 if at_period_end else 0,
            canceled_at=datetime.now(timezone.utc).isoformat(),
        )

        return result

    def update_subscription(
        self,
        subscription_id: str,
        new_price_id: str,
    ) -> dict[str, Any]:
        """Update a subscription to a new price."""
        mock = subscription_id.startswith("sub_mock_")
        provider = self._get_provider(mock)
        result = provider.update_subscription(subscription_id, new_price_id)

        self.db.update_subscription(
            subscription_id,
            stripe_price_id=new_price_id,
            status=result.get("status", "active"),
        )

        return result

    # ------------------------------------------------------------------
    # Phase 6 — Reporting
    # ------------------------------------------------------------------

    def get_mrr(self) -> float:
        """Calculate Monthly Recurring Revenue from active subscriptions.

        Returns the MRR in dollars (not cents).
        """
        active_subs = self.db.list_subscriptions(status="active")
        trialing_subs = self.db.list_subscriptions(status="trialing")
        all_subs = active_subs + trialing_subs

        total_cents = 0
        for sub in all_subs:
            amount = sub.get("amount_cents") or 0
            interval = sub.get("recurring_interval", "month")
            if interval == "year":
                total_cents += amount / 12
            elif interval == "week":
                total_cents += amount * 4.33
            else:  # month
                total_cents += amount

        return round(total_cents / 100, 2)

    def get_revenue_report(self, days: int = 30) -> dict[str, Any]:
        """Generate a revenue report for the given period.

        Returns total revenue, MRR, ARR, customer count, and average
        revenue per customer.
        """
        mrr = self.get_mrr()
        arr = round(mrr * 12, 2)

        customers = self.db.list_customers()
        active_subs = self.db.list_subscriptions(status="active")

        total_sub_revenue_cents = sum(s.get("amount_cents") or 0 for s in active_subs)
        total_revenue = round(total_sub_revenue_cents / 100, 2)

        customer_count = len(customers)
        avg_per_customer = round(total_revenue / customer_count, 2) if customer_count > 0 else 0

        return {
            "period_days": days,
            "total_revenue": total_revenue,
            "mrr": mrr,
            "arr": arr,
            "customer_count": customer_count,
            "active_subscriptions": len(active_subs),
            "avg_revenue_per_customer": avg_per_customer,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_churn_report(self, days: int = 30) -> dict[str, Any]:
        """Generate a churn report for the given period.

        Returns canceled subscription count, churn rate, and lost MRR.
        """
        canceled = self.db.list_canceled_subscriptions(days=days)
        all_subs = self.db.list_subscriptions()

        total_subs = len(all_subs)
        canceled_count = len(canceled)
        churn_rate = round(canceled_count / total_subs, 4) if total_subs > 0 else 0

        lost_mrr_cents = 0
        for sub in canceled:
            amount = sub.get("amount_cents") or 0
            interval = sub.get("recurring_interval", "month")
            if interval == "year":
                lost_mrr_cents += amount / 12
            elif interval == "week":
                lost_mrr_cents += amount * 4.33
            else:
                lost_mrr_cents += amount

        lost_mrr = round(lost_mrr_cents / 100, 2)

        return {
            "period_days": days,
            "canceled_subscriptions": canceled_count,
            "total_subscriptions": total_subs,
            "churn_rate": churn_rate,
            "churn_rate_pct": round(churn_rate * 100, 2),
            "lost_mrr": lost_mrr,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
