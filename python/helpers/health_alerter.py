"""Health Alerter -- checks system health and sends Telegram alerts on degradation."""

import logging
import os
import time

logger = logging.getLogger(__name__)

# In-process deduplication: only re-alert when status changes or after 30 min
_last_alert: dict = {"status": "healthy", "ts": 0.0}
_RESEND_INTERVAL = 1800  # re-alert every 30 min if still degraded


async def _send_telegram(message: str) -> bool:
    """Send a message to the configured Telegram chat. Returns True if sent."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_ALERT_CHAT_ID", "")
    if not (token and chat_id):
        return False
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
                timeout=10,
            )
        return True
    except Exception as e:
        logger.warning("Telegram send failed: %s", e)
        return False


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
            if _last_alert["status"] != "healthy":
                # Recovery — send one recovery notice then reset
                _last_alert.update({"status": "healthy", "ts": time.monotonic()})
                await _send_telegram("✅ Agent Jumbo recovered — status: HEALTHY")
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

        # Deduplicate: skip if same status was already alerted within _RESEND_INTERVAL
        now = time.monotonic()
        if _last_alert["status"] == status and (now - _last_alert["ts"]) < _RESEND_INTERVAL:
            return {"status": status, "alerted": False, "skipped": "deduped"}

        _last_alert.update({"status": status, "ts": now})
        alert_msg = f"⚠️ Agent Jumbo Health: {status.upper()}\n\n" + "\n".join(issues)

        # Send via Telegram
        alerted = await _send_telegram(alert_msg)
        if alerted:
            logger.info("Health alert sent to Telegram: %s", status)
            return {"status": status, "alerted": True, "issues": issues}
        else:
            logger.warning("Health alert not sent -- TELEGRAM_BOT_TOKEN or TELEGRAM_ALERT_CHAT_ID not set")
            return {"status": status, "alerted": False, "issues": issues}

    except Exception as e:
        logger.exception("Health alerter failed: %s", e)
        return {"status": "error", "alerted": False, "error": str(e)}
