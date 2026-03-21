import json
import logging
import threading
import urllib.request
from typing import Optional

log = logging.getLogger(__name__)


class TunnelWatchdog:
    _instance: Optional["TunnelWatchdog"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._interval = 60
        self._provider = "cloudflared"
        self._last_registered_url: str | None = None
        self._auto_wire_telegram = True

    @classmethod
    def get_instance(cls) -> "TunnelWatchdog":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def start(self, interval: int = 60, provider: str = "cloudflared", auto_wire_telegram: bool = True) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._interval = max(15, int(interval))
        self._provider = provider
        self._auto_wire_telegram = auto_wire_telegram
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def status(self) -> dict:
        return {
            "running": bool(self._thread and self._thread.is_alive()),
            "interval": self._interval,
            "provider": self._provider,
            "auto_wire_telegram": self._auto_wire_telegram,
            "last_registered_webhook": self._last_registered_url,
        }

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                from python.helpers import dotenv as dotenv_helper

                static_url = dotenv_helper.get_dotenv_value("TELEGRAM_WEBHOOK_URL", "")
                if static_url.startswith("https://"):
                    # Static reverse proxy mode — no tunnel needed
                    if static_url != self._last_registered_url:
                        self._register_telegram_webhook(static_url)
                else:
                    # Dynamic tunnel mode (existing behavior)
                    from python.helpers import tunnel_manager

                    manager = tunnel_manager.TunnelManager.get_instance()
                    if not manager.is_running or not manager.get_tunnel_url():
                        manager.start_tunnel(provider=self._provider)

                    tunnel_url = manager.get_tunnel_url()
                    if tunnel_url and self._auto_wire_telegram:
                        webhook_url = f"{tunnel_url}/telegram_webhook"
                        if webhook_url != self._last_registered_url:
                            self._register_telegram_webhook(webhook_url)
            except Exception as e:
                log.debug("Watchdog cycle error: %s", e)
            self._stop_event.wait(self._interval)

    def _register_telegram_webhook(self, webhook_url: str) -> None:
        from python.helpers import dotenv as dotenv_helper

        token = dotenv_helper.get_dotenv_value("TELEGRAM_BOT_TOKEN", "")
        if not token:
            log.debug("Skipping Telegram webhook registration: no TELEGRAM_BOT_TOKEN")
            return

        secret = dotenv_helper.get_dotenv_value("TELEGRAM_WEBHOOK_SECRET", "")
        payload: dict = {"url": webhook_url}
        if secret:
            payload["secret_token"] = secret

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/setWebhook",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:  # nosec B310 - hardcoded Telegram API URL
                result = json.loads(resp.read().decode())

            if result.get("ok"):
                self._last_registered_url = webhook_url
                dotenv_helper.save_dotenv_value("TELEGRAM_WEBHOOK_URL", webhook_url)
                log.info("Telegram webhook registered: %s", webhook_url)
            else:
                log.warning("Telegram setWebhook failed: %s", result)
        except Exception as e:
            log.warning("Telegram webhook registration error: %s", e)
