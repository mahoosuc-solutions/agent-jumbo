from typing import Any

from instruments.custom.finance_manager.finance_db import FinanceDatabase
from instruments.custom.finance_manager.providers.mock_provider import MockFinanceProvider
from instruments.custom.finance_manager.providers.plaid_provider import PlaidFinanceProvider
from python.helpers.audit import hash_event


class FinanceManager:
    def __init__(self, db_path: str):
        self.db = FinanceDatabase(db_path)
        self._providers = {
            "mock": MockFinanceProvider,
            "plaid": PlaidFinanceProvider,
        }

    def _get_provider(self, provider: str):
        provider_cls = self._providers.get(provider, MockFinanceProvider)
        return provider_cls()

    def get_auth_url(self, provider: str) -> str | None:
        return self._get_provider(provider).get_auth_url()

    def complete_oauth(self, account_id: int) -> dict[str, Any]:
        self.db.update_account_auth(account_id, "connected")
        return {"id": account_id, "status": "connected"}

    def connect_account(self, provider: str, mock: bool = True) -> dict[str, Any]:
        provider_key = provider if not mock else "mock"
        status = "connected" if mock else "pending"
        account_id = self.db.add_account(provider, status)
        auth_url = self._get_provider(provider_key).get_auth_url()
        self.db.add_audit(
            "finance.account_connected", hash_event("finance.account_connected", {"account_id": account_id})
        )
        return {"id": account_id, "provider": provider, "status": status, "auth_url": auth_url}

    def list_accounts(self) -> list[dict[str, Any]]:
        return self.db.list_accounts()

    def sync_transactions(self, account_id: int, start: str, end: str) -> list[dict[str, Any]]:
        provider = self._get_provider("mock")
        transactions = provider.sync_transactions({"id": account_id}, start, end)
        for txn in transactions:
            self.db.add_transaction(
                account_id,
                date=txn["date"],
                amount=txn["amount"],
                merchant=txn.get("merchant"),
                category=txn.get("category"),
            )
        self.db.add_audit(
            "finance.txn_ingested",
            hash_event("finance.txn_ingested", {"account_id": account_id, "start": start, "end": end}),
        )
        return self.db.list_transactions(account_id)

    def categorize(self, transaction_id: int, category: str) -> None:
        self.db.update_transaction(transaction_id, {"category": category})
        self.db.add_audit(
            "finance.txn_categorized",
            hash_event("finance.txn_categorized", {"transaction_id": transaction_id, "category": category}),
        )

    def upload_receipt(self, transaction_id: int, file_path: str) -> dict[str, Any]:
        ocr_text = self._run_ocr(file_path)
        receipt_id = self.db.add_receipt(transaction_id, file_path, ocr_text)
        self.db.add_audit(
            "finance.receipt_uploaded",
            hash_event("finance.receipt_uploaded", {"transaction_id": transaction_id, "file_path": file_path}),
        )
        return {"id": receipt_id, "txn_id": transaction_id, "file_path": file_path, "ocr_text": ocr_text}

    def generate_report(self, period: str, account_id: int | None = None) -> dict[str, Any]:
        transactions = self.db.list_transactions_by_period(period, account_id=account_id)
        total = sum(txn["amount"] for txn in transactions)
        summary = {"period": period, "total_count": len(transactions), "total_amount": total}
        self.db.add_report(period, summary)
        self.db.add_audit(
            "finance.report_generated",
            hash_event("finance.report_generated", {"period": period, "account_id": account_id}),
        )
        return summary

    def estimate_tax(self, period: str, account_id: int | None = None) -> dict[str, Any]:
        transactions = self.db.list_transactions_by_period(period, account_id=account_id)
        income = sum(txn["amount"] for txn in transactions if txn["amount"] > 0)
        estimate = round(income * 0.25, 2)
        self.db.add_tax_estimate(period, estimate)
        self.db.add_audit(
            "finance.tax_estimated",
            hash_event("finance.tax_estimated", {"period": period, "account_id": account_id}),
        )
        return {"period": period, "estimate": estimate}

    def roi_snapshot(self, period: str, account_id: int | None = None) -> dict[str, Any]:
        transactions = self.db.list_transactions_by_period(period, account_id=account_id)
        income = sum(txn["amount"] for txn in transactions if txn["amount"] > 0)
        expenses = abs(sum(txn["amount"] for txn in transactions if txn["amount"] < 0))
        roi = round((income - expenses) / expenses, 4) if expenses else None
        snapshot = {"period": period, "income": income, "expenses": expenses, "roi": roi}
        self.db.add_audit(
            "finance.roi_snapshot",
            hash_event("finance.roi_snapshot", {"period": period, "account_id": account_id}),
        )
        return snapshot

    def export_business_xray_data(self, period: str, account_id: int | None = None) -> dict[str, Any]:
        transactions = self.db.list_transactions_by_period(period, account_id=account_id)
        income = sum(txn["amount"] for txn in transactions if txn["amount"] > 0)
        expenses = abs(sum(txn["amount"] for txn in transactions if txn["amount"] < 0))
        profit_margin = round(((income - expenses) / income * 100), 2) if income else 0.0
        payload = {
            "monthly_revenue": income,
            "profit_margin": profit_margin,
            "growth_rate": 0.0,
            "total_customers": 0,
            "cac": 0,
            "ltv": 0,
        }
        self.db.add_audit(
            "finance.business_xray_export",
            hash_event("finance.business_xray_export", {"period": period, "account_id": account_id}),
        )
        return payload

    def _run_ocr(self, file_path: str) -> str:
        return "mock-ocr-text"

    def link_property_expense(self, transaction_id: int, property_id: int) -> dict[str, Any]:
        link_id = self.db.add_property_link(transaction_id, property_id)
        self.db.add_audit(
            "finance.property_linked",
            hash_event("finance.property_linked", {"transaction_id": transaction_id, "property_id": property_id}),
        )
        return {"id": link_id, "transaction_id": transaction_id, "property_id": property_id}
