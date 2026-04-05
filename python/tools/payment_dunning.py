"""
Payment Dunning Tool for Agent Jumbo

Manages automated failed-payment recovery (dunning) across all payment providers.
Runs an escalating retry schedule: retry → email → pause → cancel.

Actions:
  run_cycle       — execute a full dunning pass over all past-due invoices/subscriptions
  get_report      — show dunning status, pending retries, at-risk MRR
  retry_payment   — manually trigger a payment retry for a specific invoice
  configure       — update dunning schedule parameters

Example:
  {"action": "run_cycle"}
  {"action": "get_report"}
  {"action": "retry_payment", "invoice_id": "in_abc123"}
  {"action": "configure", "max_attempts": 5, "retry_intervals": {"1": 2, "2": 4, "3": 7}}
"""

import json

from python.helpers import files
from python.helpers.tool import Response, Tool


class PaymentDunning(Tool):
    def __init__(self, agent, name, method, args, message, loop_data, **kwargs):
        super().__init__(agent, name, method, args, message, loop_data, **kwargs)
        from instruments.custom.stripe_payments.dunning_manager import DunningManager
        from instruments.custom.stripe_payments.stripe_db import StripePaymentDatabase

        db_path = files.get_abs_path("./instruments/custom/stripe_payments/data/stripe_payments.db")
        self.db = StripePaymentDatabase(db_path)
        self.dunning = DunningManager(self.db)

    async def execute(self, **kwargs):
        action = (self.args.get("action") or "").lower().strip()

        action_map = {
            "run_cycle": self._run_cycle,
            "get_report": self._get_report,
            "retry_payment": self._retry_payment,
            "configure": self._configure,
        }

        handler = action_map.get(action)
        if not handler:
            return Response(
                message=json.dumps(
                    {
                        "error": f"Unknown action '{action}'",
                        "available_actions": list(action_map.keys()),
                    }
                ),
                break_loop=False,
            )

        try:
            result = await handler()
            return Response(message=json.dumps(result, indent=2, default=str), break_loop=False)
        except Exception as exc:
            return Response(
                message=json.dumps({"error": str(exc), "action": action}),
                break_loop=False,
            )

    async def _run_cycle(self):
        report = self.dunning.run_dunning_cycle()
        return {
            "status": "completed",
            "report": report.to_dict(),
        }

    async def _get_report(self):
        try:
            pending = self.dunning.get_pending_retries()
            all_attempts = self.db.list_dunning_attempts()

            # Aggregate at-risk MRR from past_due subscriptions
            past_due_subs = self.db.list_subscriptions(status="past_due")
            at_risk_cents = sum(s.get("amount_cents", 0) or 0 for s in past_due_subs)

            # Recent dunning stats
            succeeded = [a for a in all_attempts if a.get("result") == "succeeded"]
            canceled = [a for a in all_attempts if a.get("result") == "canceled"]

            return {
                "pending_retries": len(pending),
                "past_due_subscriptions": len(past_due_subs),
                "at_risk_mrr_dollars": round(at_risk_cents / 100, 2),
                "recovered_count": len(succeeded),
                "canceled_count": len(canceled),
                "dunning_config": {
                    "max_attempts": self.dunning.max_attempts,
                    "retry_intervals": self.dunning.retry_intervals,
                },
                "recent_attempts": all_attempts[:10],
            }
        except Exception as exc:
            return {"error": str(exc)}

    async def _retry_payment(self):
        invoice_id = self.args.get("invoice_id", "")
        if not invoice_id:
            return {"error": "invoice_id is required"}
        return self.dunning.retry_payment_manually(invoice_id)

    async def _configure(self):
        max_attempts = self.args.get("max_attempts")
        retry_intervals = self.args.get("retry_intervals")

        if isinstance(retry_intervals, str):
            try:
                retry_intervals = json.loads(retry_intervals)
            except (json.JSONDecodeError, TypeError):
                return {"error": 'retry_intervals must be a JSON object e.g. {"1": 3, "2": 5, "3": 7}'}

        if isinstance(retry_intervals, dict):
            # Keys come in as strings from JSON — convert to int
            retry_intervals = {int(k): int(v) for k, v in retry_intervals.items()}

        config = self.dunning.configure(
            max_attempts=int(max_attempts) if max_attempts is not None else None,
            retry_intervals=retry_intervals,
        )
        return {"status": "updated", "config": config}
