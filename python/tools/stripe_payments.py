"""
Stripe Payments Tool for Agent Jumbo
Provides agent access to Stripe payment operations: customers, products,
checkout, invoicing, subscriptions, and revenue reporting.
"""

import json

from python.helpers import files
from python.helpers.tool import Response, Tool


class StripePayments(Tool):
    def __init__(self, agent, name, method, args, message, loop_data, **kwargs):
        super().__init__(agent, name, method, args, message, loop_data, **kwargs)
        from instruments.custom.stripe_payments.stripe_manager import StripePaymentManager

        db_path = files.get_abs_path("./instruments/custom/stripe_payments/data/stripe_payments.db")
        self.manager = StripePaymentManager(db_path)

    async def execute(self, **kwargs):
        action = (self.args.get("action") or "").lower()
        mock = bool(self.args.get("mock", False))

        action_map = {
            # Customer
            "create_customer": self._create_customer,
            "sync_customer": self._sync_customer,
            "list_customers": self._list_customers,
            # Products
            "sync_product": self._sync_product,
            "sync_all_products": self._sync_all_products,
            "list_products": self._list_products,
            # Payments
            "create_checkout": self._create_checkout,
            "create_invoice": self._create_invoice,
            "list_payments": self._list_payments,
            "list_invoices": self._list_invoices,
            # Subscriptions
            "create_subscription": self._create_subscription,
            "cancel_subscription": self._cancel_subscription,
            "list_subscriptions": self._list_subscriptions,
            # Reporting
            "mrr": self._get_mrr,
            "revenue_report": self._revenue_report,
            "churn_report": self._churn_report,
            "dashboard": self._dashboard,
        }

        handler = action_map.get(action)
        if handler is None:
            return Response(message=self._format_help(), break_loop=False)

        return await handler(mock)

    # ------------------------------------------------------------------
    # Customer actions
    # ------------------------------------------------------------------

    async def _create_customer(self, mock: bool) -> Response:
        email = self.args.get("email", "")
        name = self.args.get("name", email)
        metadata = self.args.get("metadata")
        if isinstance(metadata, str):
            metadata = json.loads(metadata) if metadata else None

        result = self.manager.create_customer(email=email, name=name, metadata=metadata, mock=mock)
        return Response(message=json.dumps(result, indent=4), break_loop=False)

    async def _sync_customer(self, mock: bool) -> Response:
        lifecycle_customer_id = int(self.args.get("lifecycle_customer_id", 0))
        result = self.manager.sync_customer_from_lifecycle(lifecycle_customer_id, mock=mock)
        return Response(message=json.dumps(result, indent=4), break_loop=False)

    async def _list_customers(self, mock: bool) -> Response:
        result = self.manager.list_customers()
        return Response(
            message=json.dumps({"customers": result, "count": len(result)}, indent=4),
            break_loop=False,
        )

    # ------------------------------------------------------------------
    # Product actions
    # ------------------------------------------------------------------

    async def _sync_product(self, mock: bool) -> Response:
        portfolio_product_id = int(self.args.get("portfolio_product_id", 0))
        result = self.manager.sync_product_from_portfolio(portfolio_product_id, mock=mock)
        return Response(message=json.dumps(result, indent=4), break_loop=False)

    async def _sync_all_products(self, mock: bool) -> Response:
        results = self.manager.sync_all_listed_products(mock=mock)
        return Response(
            message=json.dumps({"synced": results, "count": len(results)}, indent=4),
            break_loop=False,
        )

    async def _list_products(self, mock: bool) -> Response:
        result = self.manager.list_products()
        return Response(
            message=json.dumps({"products": result, "count": len(result)}, indent=4),
            break_loop=False,
        )

    # ------------------------------------------------------------------
    # Payment actions
    # ------------------------------------------------------------------

    async def _create_checkout(self, mock: bool) -> Response:
        portfolio_product_id = int(self.args.get("portfolio_product_id", 0))
        customer_email = self.args.get("customer_email", "")
        result = self.manager.create_checkout_for_product(
            portfolio_product_id=portfolio_product_id,
            customer_email=customer_email,
            mock=mock,
        )
        return Response(message=json.dumps(result, indent=4), break_loop=False)

    async def _create_invoice(self, mock: bool) -> Response:
        proposal_id = int(self.args.get("proposal_id", 0))
        lifecycle_customer_id = int(self.args.get("lifecycle_customer_id", 0))
        result = self.manager.create_invoice_from_proposal(
            proposal_id=proposal_id,
            lifecycle_customer_id=lifecycle_customer_id,
            mock=mock,
        )
        return Response(message=json.dumps(result, indent=4), break_loop=False)

    async def _list_payments(self, mock: bool) -> Response:
        # Use embedded DB query directly since manager doesn't expose list_payments
        subs = self.manager.db.list_subscriptions()
        # Payments are tracked via subscriptions and invoices in the embedded schema
        invoices = self._get_all_invoices()
        return Response(
            message=json.dumps(
                {
                    "subscriptions_as_payments": len(subs),
                    "invoices": invoices,
                    "note": "Payment tracking via subscriptions and invoices.",
                },
                indent=4,
            ),
            break_loop=False,
        )

    async def _list_invoices(self, mock: bool) -> Response:
        invoices = self._get_all_invoices()
        return Response(
            message=json.dumps({"invoices": invoices, "count": len(invoices)}, indent=4),
            break_loop=False,
        )

    def _get_all_invoices(self) -> list[dict]:
        """Read all invoices from the embedded database."""
        try:
            conn = self.manager.db._connect()
            cur = conn.execute("SELECT * FROM invoices ORDER BY id DESC")
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, row)) for row in cur.fetchall()]
            conn.close()
            return rows
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Subscription actions
    # ------------------------------------------------------------------

    async def _create_subscription(self, mock: bool) -> Response:
        stripe_customer_id = self.args.get("stripe_customer_id", "")
        stripe_price_id = self.args.get("stripe_price_id", "")
        trial_days = int(self.args.get("trial_days", 0))
        result = self.manager.create_subscription(
            stripe_customer_id=stripe_customer_id,
            stripe_price_id=stripe_price_id,
            trial_days=trial_days,
            mock=mock,
        )
        return Response(message=json.dumps(result, indent=4), break_loop=False)

    async def _cancel_subscription(self, mock: bool) -> Response:
        subscription_id = self.args.get("subscription_id", "")
        at_period_end = bool(self.args.get("at_period_end", True))
        result = self.manager.cancel_subscription(subscription_id, at_period_end=at_period_end)
        return Response(message=json.dumps(result, indent=4), break_loop=False)

    async def _list_subscriptions(self, mock: bool) -> Response:
        status = self.args.get("status")
        result = self.manager.db.list_subscriptions(status=status)
        return Response(
            message=json.dumps({"subscriptions": result, "count": len(result)}, indent=4),
            break_loop=False,
        )

    # ------------------------------------------------------------------
    # Reporting actions
    # ------------------------------------------------------------------

    async def _get_mrr(self, mock: bool) -> Response:
        mrr = self.manager.get_mrr()
        return Response(
            message=json.dumps({"mrr": mrr, "mrr_formatted": f"${mrr:,.2f}"}, indent=4),
            break_loop=False,
        )

    async def _revenue_report(self, mock: bool) -> Response:
        days = int(self.args.get("days", 30))
        result = self.manager.get_revenue_report(days=days)
        return Response(message=json.dumps(result, indent=4), break_loop=False)

    async def _churn_report(self, mock: bool) -> Response:
        days = int(self.args.get("days", 30))
        result = self.manager.get_churn_report(days=days)
        return Response(message=json.dumps(result, indent=4), break_loop=False)

    async def _dashboard(self, mock: bool) -> Response:
        """Combine MRR, recent payments, active subscriptions, and revenue summary."""
        mrr = self.manager.get_mrr()
        revenue = self.manager.get_revenue_report(days=30)
        churn = self.manager.get_churn_report(days=30)
        active_subs = self.manager.db.list_subscriptions(status="active")
        customers = self.manager.list_customers()
        invoices = self._get_all_invoices()

        # Find failed payments (invoices with past_due status)
        failed_invoices = [inv for inv in invoices if inv.get("status") == "past_due"]

        dashboard = {
            "mrr": mrr,
            "mrr_formatted": f"${mrr:,.2f}",
            "arr": revenue.get("arr", 0),
            "arr_formatted": f"${revenue.get('arr', 0):,.2f}",
            "active_subscriptions": len(active_subs),
            "total_customers": len(customers),
            "revenue_30d": revenue.get("total_revenue", 0),
            "churn_rate_pct": churn.get("churn_rate_pct", 0),
            "lost_mrr": churn.get("lost_mrr", 0),
            "recent_invoices": invoices[:5],
            "failed_payments": len(failed_invoices),
            "failed_payment_details": failed_invoices[:3],
            "generated_at": revenue.get("generated_at", ""),
        }

        return Response(message=json.dumps(dashboard, indent=4), break_loop=False)

    # ------------------------------------------------------------------
    # Help
    # ------------------------------------------------------------------

    @staticmethod
    def _format_help() -> str:
        return json.dumps(
            {
                "tool": "stripe_payments",
                "actions": {
                    "Customers": {
                        "create_customer": "Create a Stripe customer. Args: email, name, metadata (optional)",
                        "sync_customer": "Sync lifecycle customer to Stripe. Args: lifecycle_customer_id",
                        "list_customers": "List all customers.",
                    },
                    "Products": {
                        "sync_product": "Sync a portfolio product to Stripe. Args: portfolio_product_id",
                        "sync_all_products": "Sync all listed portfolio products to Stripe.",
                        "list_products": "List all products.",
                    },
                    "Payments": {
                        "create_checkout": "Create checkout session. Args: portfolio_product_id, customer_email",
                        "create_invoice": "Create invoice from proposal. Args: proposal_id, lifecycle_customer_id",
                        "list_payments": "List payment activity.",
                        "list_invoices": "List all invoices.",
                    },
                    "Subscriptions": {
                        "create_subscription": "Create subscription. Args: stripe_customer_id, stripe_price_id, trial_days",
                        "cancel_subscription": "Cancel subscription. Args: subscription_id, at_period_end",
                        "list_subscriptions": "List subscriptions. Args: status (optional)",
                    },
                    "Reporting": {
                        "mrr": "Get Monthly Recurring Revenue.",
                        "revenue_report": "Generate revenue report. Args: days (default 30)",
                        "churn_report": "Generate churn report. Args: days (default 30)",
                        "dashboard": "Full payments dashboard with MRR, subscriptions, revenue, and churn.",
                    },
                },
                "common_args": {
                    "mock": "Set to true to use mock provider (default false).",
                },
            },
            indent=4,
        )
