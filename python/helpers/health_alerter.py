"""Health Alerter -- checks system health and sends Telegram alerts on degradation."""

import logging
import os

logger = logging.getLogger(__name__)


async def check_and_alert():
    """Check system health and send Telegram alert if degraded/unhealthy."""
    try:
        import httpx

        # Check health endpoint
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:80/health", timeout=10)
            health = resp.json()

        status = health.get("status", "unknown")
        if status == "healthy":
            return {"status": "healthy", "alerted": False}

        # Build alert message
        checks = health.get("checks", {})
        issues = []
        for name, check in checks.items():
            if isinstance(check, dict) and check.get("status") not in ("ok", "healthy"):
                issues.append(
                    f"- {name}: {check.get('status', 'unknown')} -- {check.get('detail', check.get('error', ''))}"
                )

        if not issues:
            return {"status": status, "alerted": False}

        alert_msg = f"Agent Jumbo Health: {status.upper()}\n\n" + "\n".join(issues)

        # Send via Telegram
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("TELEGRAM_ALERT_CHAT_ID", "")

        if token and chat_id:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": alert_msg, "parse_mode": "Markdown"},
                    timeout=10,
                )
            logger.info("Health alert sent to Telegram: %s", status)
            return {"status": status, "alerted": True, "issues": issues}
        else:
            logger.warning("Health alert not sent -- TELEGRAM_BOT_TOKEN or TELEGRAM_ALERT_CHAT_ID not set")
            return {"status": status, "alerted": False, "issues": issues}

    except Exception as e:
        logger.exception("Health alerter failed: %s", e)
        return {"status": "error", "alerted": False, "error": str(e)}
