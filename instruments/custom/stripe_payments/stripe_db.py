"""
Stripe Payments Database - SQLite storage for customers, products, prices,
payments, subscriptions, invoices, and webhook events.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any


class StripePaymentsDatabase:
    """Database operations for Stripe payments integration."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stripe_customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_customer_id TEXT UNIQUE NOT NULL,
                lifecycle_customer_id TEXT,
                email TEXT,
                name TEXT,
                metadata TEXT DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stripe_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_product_id TEXT UNIQUE NOT NULL,
                portfolio_product_id TEXT,
                name TEXT NOT NULL,
                description TEXT,
                active INTEGER DEFAULT 1,
                metadata TEXT DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stripe_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_price_id TEXT UNIQUE NOT NULL,
                stripe_product_id TEXT NOT NULL,
                unit_amount INTEGER NOT NULL,
                currency TEXT DEFAULT 'usd',
                price_type TEXT DEFAULT 'one_time',
                recurring_interval TEXT,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_payment_intent_id TEXT UNIQUE NOT NULL,
                stripe_customer_id TEXT,
                stripe_price_id TEXT,
                amount INTEGER NOT NULL,
                currency TEXT DEFAULT 'usd',
                status TEXT DEFAULT 'pending',
                payment_method TEXT,
                checkout_session_id TEXT,
                invoice_id TEXT,
                metadata TEXT DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_subscription_id TEXT UNIQUE NOT NULL,
                stripe_customer_id TEXT NOT NULL,
                stripe_price_id TEXT,
                status TEXT DEFAULT 'active',
                current_period_start TEXT,
                current_period_end TEXT,
                trial_end TEXT,
                cancel_at_period_end INTEGER DEFAULT 0,
                mrr_cents INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_invoice_id TEXT UNIQUE NOT NULL,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                amount_due INTEGER DEFAULT 0,
                amount_paid INTEGER DEFAULT 0,
                currency TEXT DEFAULT 'usd',
                status TEXT DEFAULT 'draft',
                due_date TEXT,
                paid_at TEXT,
                hosted_invoice_url TEXT,
                pdf_url TEXT,
                metadata TEXT DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS webhook_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_event_id TEXT UNIQUE NOT NULL,
                event_type TEXT NOT NULL,
                processed INTEGER DEFAULT 0,
                payload TEXT,
                error TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                processed_at TEXT
            )
        """)

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_email ON stripe_customers(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_lifecycle ON stripe_customers(lifecycle_customer_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_portfolio ON stripe_products(portfolio_product_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_webhook_event_type ON webhook_events(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_webhook_processed ON webhook_events(processed)")

        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _serialize_meta(metadata: dict[str, Any] | None) -> str:
        return json.dumps(metadata or {})

    @staticmethod
    def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return dict(row)

    # ------------------------------------------------------------------
    # Customers
    # ------------------------------------------------------------------

    def upsert_customer(
        self,
        stripe_customer_id: str,
        email: str | None = None,
        name: str | None = None,
        lifecycle_customer_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        conn = self._get_conn()
        now = self._now()
        conn.execute(
            """
            INSERT INTO stripe_customers
                (stripe_customer_id, email, name, lifecycle_customer_id, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(stripe_customer_id) DO UPDATE SET
                email = COALESCE(excluded.email, email),
                name = COALESCE(excluded.name, name),
                lifecycle_customer_id = COALESCE(excluded.lifecycle_customer_id, lifecycle_customer_id),
                metadata = excluded.metadata,
                updated_at = excluded.updated_at
            """,
            (stripe_customer_id, email, name, lifecycle_customer_id, self._serialize_meta(metadata), now, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM stripe_customers WHERE stripe_customer_id = ?", (stripe_customer_id,)
        ).fetchone()
        conn.close()
        return dict(row)

    def get_customer(self, stripe_customer_id: str) -> dict[str, Any] | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM stripe_customers WHERE stripe_customer_id = ?", (stripe_customer_id,)
        ).fetchone()
        conn.close()
        return self._row_to_dict(row)

    def get_customer_by_email(self, email: str) -> dict[str, Any] | None:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM stripe_customers WHERE email = ?", (email,)).fetchone()
        conn.close()
        return self._row_to_dict(row)

    def list_customers(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM stripe_customers ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------

    def upsert_product(
        self,
        stripe_product_id: str,
        name: str,
        description: str | None = None,
        portfolio_product_id: str | None = None,
        active: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        conn = self._get_conn()
        now = self._now()
        conn.execute(
            """
            INSERT INTO stripe_products
                (stripe_product_id, name, description, portfolio_product_id, active, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(stripe_product_id) DO UPDATE SET
                name = excluded.name,
                description = COALESCE(excluded.description, description),
                portfolio_product_id = COALESCE(excluded.portfolio_product_id, portfolio_product_id),
                active = excluded.active,
                metadata = excluded.metadata,
                updated_at = excluded.updated_at
            """,
            (
                stripe_product_id,
                name,
                description,
                portfolio_product_id,
                int(active),
                self._serialize_meta(metadata),
                now,
                now,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM stripe_products WHERE stripe_product_id = ?", (stripe_product_id,)).fetchone()
        conn.close()
        return dict(row)

    def get_product(self, stripe_product_id: str) -> dict[str, Any] | None:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM stripe_products WHERE stripe_product_id = ?", (stripe_product_id,)).fetchone()
        conn.close()
        return self._row_to_dict(row)

    def list_products(self, active_only: bool = False, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        conn = self._get_conn()
        if active_only:
            rows = conn.execute(
                "SELECT * FROM stripe_products WHERE active = 1 ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM stripe_products ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Prices
    # ------------------------------------------------------------------

    def upsert_price(
        self,
        stripe_price_id: str,
        stripe_product_id: str,
        unit_amount: int,
        currency: str = "usd",
        price_type: str = "one_time",
        recurring_interval: str | None = None,
        active: bool = True,
    ) -> dict[str, Any]:
        conn = self._get_conn()
        now = self._now()
        conn.execute(
            """
            INSERT INTO stripe_prices
                (stripe_price_id, stripe_product_id, unit_amount, currency, price_type, recurring_interval, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(stripe_price_id) DO UPDATE SET
                unit_amount = excluded.unit_amount,
                currency = excluded.currency,
                price_type = excluded.price_type,
                recurring_interval = excluded.recurring_interval,
                active = excluded.active
            """,
            (
                stripe_price_id,
                stripe_product_id,
                unit_amount,
                currency,
                price_type,
                recurring_interval,
                int(active),
                now,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM stripe_prices WHERE stripe_price_id = ?", (stripe_price_id,)).fetchone()
        conn.close()
        return dict(row)

    def get_price(self, stripe_price_id: str) -> dict[str, Any] | None:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM stripe_prices WHERE stripe_price_id = ?", (stripe_price_id,)).fetchone()
        conn.close()
        return self._row_to_dict(row)

    def list_prices(
        self, stripe_product_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[dict[str, Any]]:
        conn = self._get_conn()
        if stripe_product_id:
            rows = conn.execute(
                "SELECT * FROM stripe_prices WHERE stripe_product_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (stripe_product_id, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM stripe_prices ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Payments
    # ------------------------------------------------------------------

    def upsert_payment(
        self,
        stripe_payment_intent_id: str,
        amount: int,
        currency: str = "usd",
        status: str = "pending",
        stripe_customer_id: str | None = None,
        stripe_price_id: str | None = None,
        payment_method: str | None = None,
        checkout_session_id: str | None = None,
        invoice_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        conn = self._get_conn()
        now = self._now()
        conn.execute(
            """
            INSERT INTO payments
                (stripe_payment_intent_id, stripe_customer_id, stripe_price_id, amount, currency,
                 status, payment_method, checkout_session_id, invoice_id, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(stripe_payment_intent_id) DO UPDATE SET
                stripe_customer_id = COALESCE(excluded.stripe_customer_id, stripe_customer_id),
                stripe_price_id = COALESCE(excluded.stripe_price_id, stripe_price_id),
                amount = excluded.amount,
                currency = excluded.currency,
                status = excluded.status,
                payment_method = COALESCE(excluded.payment_method, payment_method),
                checkout_session_id = COALESCE(excluded.checkout_session_id, checkout_session_id),
                invoice_id = COALESCE(excluded.invoice_id, invoice_id),
                metadata = excluded.metadata,
                updated_at = excluded.updated_at
            """,
            (
                stripe_payment_intent_id,
                stripe_customer_id,
                stripe_price_id,
                amount,
                currency,
                status,
                payment_method,
                checkout_session_id,
                invoice_id,
                self._serialize_meta(metadata),
                now,
                now,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM payments WHERE stripe_payment_intent_id = ?", (stripe_payment_intent_id,)
        ).fetchone()
        conn.close()
        return dict(row)

    def get_payment(self, stripe_payment_intent_id: str) -> dict[str, Any] | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM payments WHERE stripe_payment_intent_id = ?", (stripe_payment_intent_id,)
        ).fetchone()
        conn.close()
        return self._row_to_dict(row)

    def list_payments(
        self, stripe_customer_id: str | None = None, status: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[dict[str, Any]]:
        conn = self._get_conn()
        clauses: list[str] = []
        params: list[Any] = []
        if stripe_customer_id:
            clauses.append("stripe_customer_id = ?")
            params.append(stripe_customer_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.extend([limit, offset])
        rows = conn.execute(
            f"SELECT * FROM payments {where} ORDER BY created_at DESC LIMIT ? OFFSET ?", params
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_payment_status(self, stripe_payment_intent_id: str, status: str) -> dict[str, Any] | None:
        conn = self._get_conn()
        conn.execute(
            "UPDATE payments SET status = ?, updated_at = ? WHERE stripe_payment_intent_id = ?",
            (status, self._now(), stripe_payment_intent_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM payments WHERE stripe_payment_intent_id = ?", (stripe_payment_intent_id,)
        ).fetchone()
        conn.close()
        return self._row_to_dict(row)

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    def upsert_subscription(
        self,
        stripe_subscription_id: str,
        stripe_customer_id: str,
        stripe_price_id: str | None = None,
        status: str = "active",
        current_period_start: str | None = None,
        current_period_end: str | None = None,
        trial_end: str | None = None,
        cancel_at_period_end: bool = False,
        mrr_cents: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        conn = self._get_conn()
        now = self._now()
        conn.execute(
            """
            INSERT INTO subscriptions
                (stripe_subscription_id, stripe_customer_id, stripe_price_id, status,
                 current_period_start, current_period_end, trial_end, cancel_at_period_end,
                 mrr_cents, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(stripe_subscription_id) DO UPDATE SET
                stripe_customer_id = excluded.stripe_customer_id,
                stripe_price_id = COALESCE(excluded.stripe_price_id, stripe_price_id),
                status = excluded.status,
                current_period_start = COALESCE(excluded.current_period_start, current_period_start),
                current_period_end = COALESCE(excluded.current_period_end, current_period_end),
                trial_end = excluded.trial_end,
                cancel_at_period_end = excluded.cancel_at_period_end,
                mrr_cents = excluded.mrr_cents,
                metadata = excluded.metadata,
                updated_at = excluded.updated_at
            """,
            (
                stripe_subscription_id,
                stripe_customer_id,
                stripe_price_id,
                status,
                current_period_start,
                current_period_end,
                trial_end,
                int(cancel_at_period_end),
                mrr_cents,
                self._serialize_meta(metadata),
                now,
                now,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM subscriptions WHERE stripe_subscription_id = ?", (stripe_subscription_id,)
        ).fetchone()
        conn.close()
        return dict(row)

    def get_subscription(self, stripe_subscription_id: str) -> dict[str, Any] | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM subscriptions WHERE stripe_subscription_id = ?", (stripe_subscription_id,)
        ).fetchone()
        conn.close()
        return self._row_to_dict(row)

    def list_subscriptions(
        self, stripe_customer_id: str | None = None, status: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[dict[str, Any]]:
        conn = self._get_conn()
        clauses: list[str] = []
        params: list[Any] = []
        if stripe_customer_id:
            clauses.append("stripe_customer_id = ?")
            params.append(stripe_customer_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.extend([limit, offset])
        rows = conn.execute(
            f"SELECT * FROM subscriptions {where} ORDER BY created_at DESC LIMIT ? OFFSET ?", params
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_subscription_status(self, stripe_subscription_id: str, status: str) -> dict[str, Any] | None:
        conn = self._get_conn()
        conn.execute(
            "UPDATE subscriptions SET status = ?, updated_at = ? WHERE stripe_subscription_id = ?",
            (status, self._now(), stripe_subscription_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM subscriptions WHERE stripe_subscription_id = ?", (stripe_subscription_id,)
        ).fetchone()
        conn.close()
        return self._row_to_dict(row)

    # ------------------------------------------------------------------
    # Invoices
    # ------------------------------------------------------------------

    def upsert_invoice(
        self,
        stripe_invoice_id: str,
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
        amount_due: int = 0,
        amount_paid: int = 0,
        currency: str = "usd",
        status: str = "draft",
        due_date: str | None = None,
        paid_at: str | None = None,
        hosted_invoice_url: str | None = None,
        pdf_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        conn = self._get_conn()
        now = self._now()
        conn.execute(
            """
            INSERT INTO invoices
                (stripe_invoice_id, stripe_customer_id, stripe_subscription_id, amount_due, amount_paid,
                 currency, status, due_date, paid_at, hosted_invoice_url, pdf_url, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(stripe_invoice_id) DO UPDATE SET
                stripe_customer_id = COALESCE(excluded.stripe_customer_id, stripe_customer_id),
                stripe_subscription_id = COALESCE(excluded.stripe_subscription_id, stripe_subscription_id),
                amount_due = excluded.amount_due,
                amount_paid = excluded.amount_paid,
                currency = excluded.currency,
                status = excluded.status,
                due_date = COALESCE(excluded.due_date, due_date),
                paid_at = excluded.paid_at,
                hosted_invoice_url = COALESCE(excluded.hosted_invoice_url, hosted_invoice_url),
                pdf_url = COALESCE(excluded.pdf_url, pdf_url),
                metadata = excluded.metadata,
                updated_at = excluded.updated_at
            """,
            (
                stripe_invoice_id,
                stripe_customer_id,
                stripe_subscription_id,
                amount_due,
                amount_paid,
                currency,
                status,
                due_date,
                paid_at,
                hosted_invoice_url,
                pdf_url,
                self._serialize_meta(metadata),
                now,
                now,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM invoices WHERE stripe_invoice_id = ?", (stripe_invoice_id,)).fetchone()
        conn.close()
        return dict(row)

    def get_invoice(self, stripe_invoice_id: str) -> dict[str, Any] | None:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM invoices WHERE stripe_invoice_id = ?", (stripe_invoice_id,)).fetchone()
        conn.close()
        return self._row_to_dict(row)

    def list_invoices(
        self, stripe_customer_id: str | None = None, status: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[dict[str, Any]]:
        conn = self._get_conn()
        clauses: list[str] = []
        params: list[Any] = []
        if stripe_customer_id:
            clauses.append("stripe_customer_id = ?")
            params.append(stripe_customer_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.extend([limit, offset])
        rows = conn.execute(
            f"SELECT * FROM invoices {where} ORDER BY created_at DESC LIMIT ? OFFSET ?", params
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_invoice_status(self, stripe_invoice_id: str, status: str) -> dict[str, Any] | None:
        conn = self._get_conn()
        conn.execute(
            "UPDATE invoices SET status = ?, updated_at = ? WHERE stripe_invoice_id = ?",
            (status, self._now(), stripe_invoice_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM invoices WHERE stripe_invoice_id = ?", (stripe_invoice_id,)).fetchone()
        conn.close()
        return self._row_to_dict(row)

    # ------------------------------------------------------------------
    # Webhook Events
    # ------------------------------------------------------------------

    def record_webhook_event(
        self,
        stripe_event_id: str,
        event_type: str,
        payload: str,
    ) -> dict[str, Any]:
        conn = self._get_conn()
        now = self._now()
        conn.execute(
            """
            INSERT INTO webhook_events (stripe_event_id, event_type, payload, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(stripe_event_id) DO NOTHING
            """,
            (stripe_event_id, event_type, payload, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM webhook_events WHERE stripe_event_id = ?", (stripe_event_id,)).fetchone()
        conn.close()
        return dict(row)

    def mark_event_processed(self, stripe_event_id: str, error: str | None = None) -> dict[str, Any] | None:
        conn = self._get_conn()
        now = self._now()
        conn.execute(
            "UPDATE webhook_events SET processed = 1, processed_at = ?, error = ? WHERE stripe_event_id = ?",
            (now, error, stripe_event_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM webhook_events WHERE stripe_event_id = ?", (stripe_event_id,)).fetchone()
        conn.close()
        return self._row_to_dict(row)

    def get_webhook_event(self, stripe_event_id: str) -> dict[str, Any] | None:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM webhook_events WHERE stripe_event_id = ?", (stripe_event_id,)).fetchone()
        conn.close()
        return self._row_to_dict(row)

    def list_webhook_events(
        self, event_type: str | None = None, processed: bool | None = None, limit: int = 100, offset: int = 0
    ) -> list[dict[str, Any]]:
        conn = self._get_conn()
        clauses: list[str] = []
        params: list[Any] = []
        if event_type:
            clauses.append("event_type = ?")
            params.append(event_type)
        if processed is not None:
            clauses.append("processed = ?")
            params.append(int(processed))
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.extend([limit, offset])
        rows = conn.execute(
            f"SELECT * FROM webhook_events {where} ORDER BY created_at DESC LIMIT ? OFFSET ?", params
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
