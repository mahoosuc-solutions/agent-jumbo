"""
Stripe Payments Database - SQLite storage for customers, products, prices,
payments, subscriptions, invoices, and webhook events.
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
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


# ---------------------------------------------------------------------------
# Lightweight DB used by StripePaymentManager (moved from stripe_manager.py)
# ---------------------------------------------------------------------------


class StripePaymentDatabase:
    """SQLite backend for local Stripe payment records.

    Simpler schema than StripePaymentsDatabase -- used by
    StripePaymentManager for cross-system sync bookkeeping.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stripe_customer_id TEXT UNIQUE,
                    email TEXT,
                    name TEXT,
                    metadata TEXT,
                    lifecycle_customer_id INTEGER,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stripe_product_id TEXT UNIQUE,
                    stripe_price_id TEXT,
                    name TEXT NOT NULL,
                    description TEXT,
                    amount_cents INTEGER,
                    currency TEXT DEFAULT 'usd',
                    price_model TEXT DEFAULT 'one-time',
                    recurring_interval TEXT,
                    portfolio_product_id INTEGER,
                    metadata TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stripe_invoice_id TEXT UNIQUE,
                    stripe_customer_id TEXT,
                    status TEXT DEFAULT 'draft',
                    amount_due INTEGER DEFAULT 0,
                    currency TEXT DEFAULT 'usd',
                    hosted_url TEXT,
                    pdf_url TEXT,
                    proposal_id INTEGER,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    finalized_at TEXT
                );

                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stripe_subscription_id TEXT UNIQUE,
                    stripe_customer_id TEXT,
                    stripe_price_id TEXT,
                    status TEXT DEFAULT 'active',
                    current_period_start TEXT,
                    current_period_end TEXT,
                    cancel_at_period_end INTEGER DEFAULT 0,
                    canceled_at TEXT,
                    amount_cents INTEGER DEFAULT 0,
                    currency TEXT DEFAULT 'usd',
                    recurring_interval TEXT DEFAULT 'month',
                    metadata TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
                CREATE INDEX IF NOT EXISTS idx_customers_lifecycle ON customers(lifecycle_customer_id);
                CREATE INDEX IF NOT EXISTS idx_products_portfolio ON products(portfolio_product_id);
                CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
                """
            )
            # Schema migrations: add multi-provider columns if they don't exist yet.
            for migration in [
                "ALTER TABLE customers ADD COLUMN payment_provider TEXT DEFAULT 'stripe'",
                "ALTER TABLE customers ADD COLUMN provider_customer_id TEXT",
                "ALTER TABLE subscriptions ADD COLUMN payment_provider TEXT DEFAULT 'stripe'",
                "ALTER TABLE invoices ADD COLUMN payment_provider TEXT DEFAULT 'stripe'",
            ]:
                try:
                    conn.execute(migration)
                except Exception:
                    pass  # Column already exists

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # -- customers -----------------------------------------------------------

    def add_customer(
        self,
        stripe_customer_id: str,
        email: str,
        name: str,
        metadata: dict | None = None,
        lifecycle_customer_id: int | None = None,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO customers
                    (stripe_customer_id, email, name, metadata, lifecycle_customer_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    stripe_customer_id,
                    email,
                    name,
                    json.dumps(metadata) if metadata else None,
                    lifecycle_customer_id,
                    self._now(),
                ),
            )
            return int(cur.lastrowid)

    def get_customer(self, customer_id: int | None = None, email: str | None = None) -> dict | None:
        with self._connect() as conn:
            if customer_id is not None:
                cur = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
            elif email is not None:
                cur = conn.execute("SELECT * FROM customers WHERE email = ?", (email,))
            else:
                return None
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
        if row is None:
            return None
        return dict(zip(cols, row))

    def get_customer_by_lifecycle_id(self, lifecycle_customer_id: int) -> dict | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM customers WHERE lifecycle_customer_id = ?",
                (lifecycle_customer_id,),
            )
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
        if row is None:
            return None
        return dict(zip(cols, row))

    def list_customers(self) -> list[dict]:
        with self._connect() as conn:
            cur = conn.execute("SELECT * FROM customers ORDER BY id ASC")
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    # -- products ------------------------------------------------------------

    def add_product(
        self,
        stripe_product_id: str,
        name: str,
        description: str | None = None,
        stripe_price_id: str | None = None,
        amount_cents: int | None = None,
        currency: str = "usd",
        price_model: str = "one-time",
        recurring_interval: str | None = None,
        portfolio_product_id: int | None = None,
        metadata: dict | None = None,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO products
                    (stripe_product_id, name, description, stripe_price_id,
                     amount_cents, currency, price_model, recurring_interval,
                     portfolio_product_id, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stripe_product_id,
                    name,
                    description,
                    stripe_price_id,
                    amount_cents,
                    currency,
                    price_model,
                    recurring_interval,
                    portfolio_product_id,
                    json.dumps(metadata) if metadata else None,
                    self._now(),
                ),
            )
            return int(cur.lastrowid)

    def get_product(self, product_id: int | None = None, stripe_product_id: str | None = None) -> dict | None:
        with self._connect() as conn:
            if product_id is not None:
                cur = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            elif stripe_product_id is not None:
                cur = conn.execute("SELECT * FROM products WHERE stripe_product_id = ?", (stripe_product_id,))
            else:
                return None
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
        if row is None:
            return None
        return dict(zip(cols, row))

    def get_product_by_portfolio_id(self, portfolio_product_id: int) -> dict | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM products WHERE portfolio_product_id = ?",
                (portfolio_product_id,),
            )
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
        if row is None:
            return None
        return dict(zip(cols, row))

    def update_product(self, product_id: int, **kwargs: Any) -> None:
        if not kwargs:
            return
        columns = ", ".join(f"{k} = ?" for k in kwargs)
        params = [*list(kwargs.values()), product_id]
        with self._connect() as conn:
            conn.execute(f"UPDATE products SET {columns} WHERE id = ?", params)  # nosec B608

    def list_products(self) -> list[dict]:
        with self._connect() as conn:
            cur = conn.execute("SELECT * FROM products ORDER BY id ASC")
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    # -- invoices ------------------------------------------------------------

    def add_invoice(
        self,
        stripe_invoice_id: str,
        stripe_customer_id: str,
        status: str = "draft",
        amount_due: int = 0,
        currency: str = "usd",
        hosted_url: str | None = None,
        pdf_url: str | None = None,
        proposal_id: int | None = None,
        metadata: dict | None = None,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO invoices
                    (stripe_invoice_id, stripe_customer_id, status, amount_due,
                     currency, hosted_url, pdf_url, proposal_id, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stripe_invoice_id,
                    stripe_customer_id,
                    status,
                    amount_due,
                    currency,
                    hosted_url,
                    pdf_url,
                    proposal_id,
                    json.dumps(metadata) if metadata else None,
                    self._now(),
                ),
            )
            return int(cur.lastrowid)

    def update_invoice(self, stripe_invoice_id: str, **kwargs: Any) -> None:
        if not kwargs:
            return
        columns = ", ".join(f"{k} = ?" for k in kwargs)
        params = [*list(kwargs.values()), stripe_invoice_id]
        with self._connect() as conn:
            conn.execute(f"UPDATE invoices SET {columns} WHERE stripe_invoice_id = ?", params)  # nosec B608

    # -- subscriptions -------------------------------------------------------

    def add_subscription(
        self,
        stripe_subscription_id: str,
        stripe_customer_id: str,
        stripe_price_id: str,
        status: str = "active",
        current_period_start: str | None = None,
        current_period_end: str | None = None,
        amount_cents: int = 0,
        currency: str = "usd",
        recurring_interval: str = "month",
        metadata: dict | None = None,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO subscriptions
                    (stripe_subscription_id, stripe_customer_id, stripe_price_id,
                     status, current_period_start, current_period_end,
                     amount_cents, currency, recurring_interval, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stripe_subscription_id,
                    stripe_customer_id,
                    stripe_price_id,
                    status,
                    current_period_start,
                    current_period_end,
                    amount_cents,
                    currency,
                    recurring_interval,
                    json.dumps(metadata) if metadata else None,
                    self._now(),
                ),
            )
            return int(cur.lastrowid)

    def update_subscription(self, stripe_subscription_id: str, **kwargs: Any) -> None:
        if not kwargs:
            return
        columns = ", ".join(f"{k} = ?" for k in kwargs)
        params = [*list(kwargs.values()), stripe_subscription_id]
        with self._connect() as conn:
            conn.execute(
                f"UPDATE subscriptions SET {columns} WHERE stripe_subscription_id = ?",  # nosec B608
                params,
            )

    def list_subscriptions(self, status: str | None = None) -> list[dict]:
        with self._connect() as conn:
            if status:
                cur = conn.execute(
                    "SELECT * FROM subscriptions WHERE status = ? ORDER BY id ASC",
                    (status,),
                )
            else:
                cur = conn.execute("SELECT * FROM subscriptions ORDER BY id ASC")
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def list_subscriptions_by_period(self, days: int = 30) -> list[dict]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM subscriptions WHERE created_at >= ? ORDER BY id ASC",
                (cutoff,),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def list_subscriptions_by_customer(self, stripe_customer_id: str) -> list[dict]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM subscriptions WHERE stripe_customer_id = ? ORDER BY id ASC",
                (stripe_customer_id,),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def list_invoices_by_customer(self, stripe_customer_id: str) -> list[dict]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM invoices WHERE stripe_customer_id = ? ORDER BY created_at DESC",
                (stripe_customer_id,),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def update_payment_status(self, payment_id: str, status: str) -> None:
        """Update a payment record status (used by webhook handlers)."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE subscriptions SET status = ? WHERE stripe_subscription_id = ?",
                (status, payment_id),
            )

    def update_invoice_status(self, invoice_id: str, status: str) -> None:
        """Update an invoice record status (used by webhook handlers)."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE invoices SET status = ? WHERE stripe_invoice_id = ?",
                (status, invoice_id),
            )

    def record_webhook_event(self, event_id: str, event_type: str, payload: str) -> None:
        """Record a webhook event (Square/PayPal use same table via event_id)."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO subscriptions (stripe_subscription_id, stripe_customer_id, created_at)
                VALUES (?, '', ?)
                """,
                (f"__webhook_noop_{event_id}", self._now()),
            )

    def get_webhook_event(self, event_id: str) -> dict | None:
        """Check if a webhook event ID was already processed."""
        return None  # Placeholder — full deduplication via webhook_events table

    def mark_webhook_processed(self, event_id: str) -> None:
        pass  # Placeholder — used by Square/PayPal webhook handlers

    def mark_webhook_error(self, event_id: str, error: str) -> None:
        pass  # Placeholder

    # -- dunning tables (added via migration) --------------------------------

    def _ensure_dunning_schema(self) -> None:
        """Add dunning tables and helper columns. Called lazily on first dunning use."""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS dunning_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id TEXT NOT NULL,
                    customer_id TEXT,
                    attempt_number INTEGER DEFAULT 1,
                    result TEXT DEFAULT 'pending',
                    email_sent INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dunning_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT DEFAULT 'all',
                    max_attempts INTEGER DEFAULT 4,
                    retry_intervals_days TEXT DEFAULT '[3,5,7]',
                    pause_threshold INTEGER DEFAULT 3,
                    cancel_threshold INTEGER DEFAULT 4,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_dunning_item ON dunning_attempts(item_id);
                CREATE INDEX IF NOT EXISTS idx_dunning_customer ON dunning_attempts(customer_id);
            """)

    def record_dunning_attempt(
        self,
        item_id: str,
        customer_id: str,
        attempt_number: int,
        result: str,
        email_sent: bool = False,
    ) -> None:
        self._ensure_dunning_schema()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO dunning_attempts
                    (item_id, customer_id, attempt_number, result, email_sent, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (item_id, customer_id, attempt_number, result, int(email_sent), self._now()),
            )

    def list_dunning_attempts_for_item(self, item_id: str) -> list[dict]:
        self._ensure_dunning_schema()
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM dunning_attempts WHERE item_id = ? ORDER BY id ASC",
                (item_id,),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def list_dunning_attempts(self, status: str | None = None) -> list[dict]:
        self._ensure_dunning_schema()
        with self._connect() as conn:
            if status:
                cur = conn.execute(
                    "SELECT * FROM dunning_attempts WHERE result = ? ORDER BY created_at DESC LIMIT 200",
                    (status,),
                )
            else:
                cur = conn.execute("SELECT * FROM dunning_attempts ORDER BY created_at DESC LIMIT 200")
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def list_invoices_by_status(self, status: str) -> list[dict]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM invoices WHERE status = ? ORDER BY created_at DESC",
                (status,),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def get_invoice_by_id(self, invoice_id: str) -> dict | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM invoices WHERE stripe_invoice_id = ?",
                (invoice_id,),
            )
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
        if row is None:
            return None
        return dict(zip(cols, row))

    def list_canceled_subscriptions(self, days: int = 30) -> list[dict]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT * FROM subscriptions
                WHERE status IN ('canceled', 'cancelled')
                  AND canceled_at >= ?
                ORDER BY id ASC
                """,
                (cutoff,),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
