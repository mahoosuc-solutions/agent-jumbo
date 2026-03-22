"""
Finance Report Tool

Generates financial reports (income, balance, cashflow, P&L) from live
transaction data in the finance manager database. Falls back to sample
data when no transactions are available.
"""

import logging
from datetime import datetime, timezone

from python.helpers import files
from python.helpers.tool import Response, Tool

logger = logging.getLogger(__name__)


class FinanceReport(Tool):
    async def execute(self, **kwargs):
        report_type = self.args.get("type", "income")
        period = self.args.get("period", "month")

        valid_types = ["income", "balance", "cashflow", "pnl"]
        if report_type not in valid_types:
            return Response(
                message=f"Invalid report type: {report_type}. Must be one of: {', '.join(valid_types)}",
                break_loop=False,
            )

        valid_periods = ["month", "quarter", "year"]
        if period not in valid_periods:
            return Response(
                message=f"Invalid period: {period}. Must be one of: {', '.join(valid_periods)}",
                break_loop=False,
            )

        transactions = self._load_transactions(period)
        report = self._generate_report(report_type, period, transactions)

        source = "live data" if transactions else "sample data"
        return Response(
            message=f"# Financial Report: {report_type.upper()}\n\n"
            f"**Period**: {period}\n"
            f"**Source**: {source} ({len(transactions)} transactions)\n\n"
            f"{report}",
            break_loop=False,
        )

    def _load_transactions(self, period: str) -> list[dict]:
        """Load transactions from the finance database for the given period."""
        try:
            from instruments.custom.finance_manager.finance_db import FinanceDatabase

            db_path = files.get_abs_path("./instruments/custom/finance_manager/data/finance.db")
            db = FinanceDatabase(db_path)

            now = datetime.now(timezone.utc)
            if period == "month":
                period_prefix = now.strftime("%Y-%m")
            elif period == "quarter":
                quarter_start_month = ((now.month - 1) // 3) * 3 + 1
                period_prefix = f"{now.year}-{quarter_start_month:02d}"
            else:
                period_prefix = str(now.year)

            return db.list_transactions_by_period(period_prefix)
        except Exception as e:
            logger.debug("Could not load transactions: %s", e)
            return []

    def _generate_report(self, report_type: str, period: str, transactions: list[dict]) -> str:
        """Generate report from transaction data, or sample data if none available."""
        if not transactions:
            return self._sample_report(report_type, period)

        income = sum(t["amount"] for t in transactions if t["amount"] > 0)
        expenses = sum(abs(t["amount"]) for t in transactions if t["amount"] < 0)
        net = income - expenses

        # Group by category
        by_category: dict[str, float] = {}
        for t in transactions:
            cat = t.get("category") or "uncategorized"
            by_category[cat] = by_category.get(cat, 0) + t["amount"]

        if report_type == "income":
            return self._income_report(period, income, expenses, net, by_category)
        elif report_type == "pnl":
            return self._pnl_report(period, income, expenses, net)
        elif report_type == "cashflow":
            return self._cashflow_report(period, income, expenses, net, by_category)
        else:  # balance
            return self._balance_report(period, income, expenses, net)

    def _income_report(self, period: str, income: float, expenses: float, net: float, by_category: dict) -> str:
        revenue_lines = []
        expense_lines = []
        for cat, amount in sorted(by_category.items()):
            if amount > 0:
                revenue_lines.append(f"- {cat}: ${amount:,.2f}")
            else:
                expense_lines.append(f"- {cat}: ${abs(amount):,.2f}")

        return (
            f"## Income Statement ({period.capitalize()})\n\n"
            f"**Revenue**\n"
            + "\n".join(revenue_lines or ["- No revenue recorded"])
            + f"\n**Total Revenue**: ${income:,.2f}\n\n"
            f"**Expenses**\n"
            + "\n".join(expense_lines or ["- No expenses recorded"])
            + f"\n**Total Expenses**: ${expenses:,.2f}\n\n"
            f"**Net Income**: ${net:,.2f}"
        )

    def _pnl_report(self, period: str, income: float, expenses: float, net: float) -> str:
        gross_margin = (income - expenses) / income * 100 if income else 0
        return (
            f"## Profit & Loss ({period.capitalize()})\n\n"
            f"**Income**\n"
            f"- Gross Revenue: ${income:,.2f}\n"
            f"- Total Expenses: ${expenses:,.2f}\n"
            f"- Net Profit: ${net:,.2f}\n\n"
            f"**Margins**\n"
            f"- Gross Margin: {gross_margin:.1f}%\n"
            f"- Net Margin: {(net / income * 100) if income else 0:.1f}%"
        )

    def _cashflow_report(self, period: str, income: float, expenses: float, net: float, by_category: dict) -> str:
        ops_income = sum(v for v in by_category.values() if v > 0)
        ops_expense = sum(abs(v) for v in by_category.values() if v < 0)
        return (
            f"## Cash Flow Statement ({period.capitalize()})\n\n"
            f"**Operating Activities**\n"
            f"- Cash Inflows: ${ops_income:,.2f}\n"
            f"- Cash Outflows: -${ops_expense:,.2f}\n"
            f"**Net Cash from Operations**: ${net:,.2f}\n\n"
            f"**Net Cash Change**: ${net:,.2f}"
        )

    def _balance_report(self, period: str, income: float, expenses: float, net: float) -> str:
        return (
            f"## Balance Summary ({period.capitalize()})\n\n"
            f"**Period Activity**\n"
            f"- Total Inflows: ${income:,.2f}\n"
            f"- Total Outflows: ${expenses:,.2f}\n"
            f"- Net Position: ${net:,.2f}\n\n"
            f"*Connect an accounting system for full balance sheet data.*"
        )

    def _sample_report(self, report_type: str, period: str) -> str:
        """Fallback sample reports when no transaction data is available."""
        samples = {
            "income": (
                f"## Income Statement ({period.capitalize()}) — Sample Data\n\n"
                "**Revenue**\n- Product Sales: $125,000\n- Service Revenue: $45,000\n"
                "**Total Revenue**: $175,000\n\n"
                "**Expenses**\n- COGS: $62,500\n- Operating: $45,000\n- Marketing: $15,000\n"
                "**Total Expenses**: $122,500\n\n"
                "**Net Income**: $52,500\n\n"
                "*No live transaction data found. Connect a finance provider to see real numbers.*"
            ),
            "balance": (
                f"## Balance Sheet ({period.capitalize()}) — Sample Data\n\n"
                "**Assets**: $400,000\n**Liabilities**: $200,000\n**Equity**: $200,000\n\n"
                "*Connect an accounting system for real balance data.*"
            ),
            "cashflow": (
                f"## Cash Flow ({period.capitalize()}) — Sample Data\n\n"
                "**Operating**: -$10,000\n**Investing**: -$15,000\n**Financing**: $50,000\n"
                "**Net Change**: $25,000\n\n"
                "*Connect a finance provider to see real cash flow.*"
            ),
            "pnl": (
                f"## P&L ({period.capitalize()}) — Sample Data\n\n"
                "**Revenue**: $175,000\n**Expenses**: $157,500\n**Net Profit**: $17,500\n"
                "**Net Margin**: 10.0%\n\n"
                "*Connect a finance provider to see real P&L.*"
            ),
        }
        return samples[report_type]
