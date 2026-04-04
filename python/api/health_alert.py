"""Trigger a health check and send Telegram alert if degraded.

POST /health_alert — called by the platform-health-monitor scheduler task.
Returns immediately with the alert result. Designed for loopback use.
"""

from python.helpers.api import ApiHandler, Input, Output, Request


class HealthAlert(ApiHandler):
    @classmethod
    def requires_loopback(cls) -> bool:
        return True

    async def process(self, input: Input, request: Request) -> Output:
        from python.helpers.health_alerter import check_and_alert

        result = await check_and_alert()
        return {"ok": True, **result}
