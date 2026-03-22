import json
import sqlite3
from typing import Any

from python.helpers.datetime_utils import isoformat_z, utc_now


class FinanceDatabase:
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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    merchant TEXT,
                    category TEXT,
                    status TEXT DEFAULT 'posted',
                    FOREIGN KEY(account_id) REFERENCES accounts(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS receipts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    txn_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    ocr_text TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(txn_id) REFERENCES transactions(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tax_estimates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period TEXT NOT NULL,
                    estimate REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS property_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    txn_id INTEGER NOT NULL,
                    property_id INTEGER NOT NULL,
                    FOREIGN KEY(txn_id) REFERENCES transactions(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def add_account(self, provider: str, status: str) -> int:
        created_at = isoformat_z(utc_now())
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO accounts (provider, status, created_at)
                VALUES (?, ?, ?)
                """,
                (provider, status, created_at),
            )
            return int(cursor.lastrowid)

    def update_account_auth(self, account_id: int, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE accounts
                SET status = ?
                WHERE id = ?
                """,
                (status, account_id),
            )

    def get_account(self, account_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, provider, status, created_at
                FROM accounts
                WHERE id = ?
                """,
                (account_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "provider": row[1],
            "status": row[2],
            "created_at": row[3],
        }

    def list_accounts(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, provider, status, created_at
                FROM accounts
                ORDER BY id ASC
                """
            ).fetchall()
        return [
            {
                "id": row[0],
                "provider": row[1],
                "status": row[2],
                "created_at": row[3],
            }
            for row in rows
        ]

    def add_transaction(
        self,
        account_id: int,
        date: str,
        amount: float,
        merchant: str | None = None,
        category: str | None = None,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO transactions (account_id, date, amount, merchant, category)
                VALUES (?, ?, ?, ?, ?)
                """,
                (account_id, date, amount, merchant, category),
            )
            return int(cursor.lastrowid)

    def list_transactions(self, account_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, account_id, date, amount, merchant, category, status
                FROM transactions
                WHERE account_id = ?
                ORDER BY id ASC
                """,
                (account_id,),
            ).fetchall()
        return [
            {
                "id": row[0],
                "account_id": row[1],
                "date": row[2],
                "amount": row[3],
                "merchant": row[4],
                "category": row[5],
                "status": row[6],
            }
            for row in rows
        ]

    def list_transactions_by_period(self, period: str, account_id: int | None = None) -> list[dict[str, Any]]:
        params: list[Any] = [f"{period}%"]
        account_clause = ""
        if account_id is not None:
            account_clause = "AND account_id = ?"
            params.append(account_id)
        with self._connect() as conn:
            rows = conn.execute(  # nosec B608 - controlled query construction
                f"""
                SELECT id, account_id, date, amount, merchant, category, status
                FROM transactions
                WHERE date LIKE ?
                {account_clause}
                ORDER BY id ASC
                """,
                tuple(params),
            ).fetchall()
        return [
            {
                "id": row[0],
                "account_id": row[1],
                "date": row[2],
                "amount": row[3],
                "merchant": row[4],
                "category": row[5],
                "status": row[6],
            }
            for row in rows
        ]

    def update_transaction(self, txn_id: int, updates: dict[str, Any]) -> None:
        if not updates:
            return
        columns = ", ".join([f"{key} = ?" for key in updates])
        params = [*list(updates.values()), txn_id]
        with self._connect() as conn:
            conn.execute(f"UPDATE transactions SET {columns} WHERE id = ?", params)  # nosec B608 - controlled query construction

    def add_receipt(self, txn_id: int, file_path: str, ocr_text: str) -> int:
        created_at = isoformat_z(utc_now())
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO receipts (txn_id, file_path, ocr_text, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (txn_id, file_path, ocr_text, created_at),
            )
            return int(cursor.lastrowid)

    def add_report(self, period: str, summary: dict[str, Any]) -> int:
        created_at = isoformat_z(utc_now())
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO reports (period, summary, created_at)
                VALUES (?, ?, ?)
                """,
                (period, json.dumps(summary), created_at),
            )
            return int(cursor.lastrowid)

    def add_tax_estimate(self, period: str, estimate: float) -> int:
        created_at = isoformat_z(utc_now())
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tax_estimates (period, estimate, created_at)
                VALUES (?, ?, ?)
                """,
                (period, estimate, created_at),
            )
            return int(cursor.lastrowid)

    def add_property_link(self, txn_id: int, property_id: int) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO property_links (txn_id, property_id)
                VALUES (?, ?)
                """,
                (txn_id, property_id),
            )
            return int(cursor.lastrowid)

    def add_audit(self, event_type: str, event_hash: str) -> int:
        created_at = isoformat_z(utc_now())
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO audit (event_type, event_hash, created_at)
                VALUES (?, ?, ?)
                """,
                (event_type, event_hash, created_at),
            )
            return int(cursor.lastrowid)
