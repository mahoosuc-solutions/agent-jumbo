"""Viber channel adapter."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request
from typing import Any

from python.helpers.channel_bridge import ChannelBridge, ChannelStatus, NormalizedMessage

try:
    from python.helpers.channel_factory import ChannelFactory
except ImportError:  # pragma: no cover
    ChannelFactory = None  # type: ignore[assignment,misc]


def _register(cls: type) -> type:
    if ChannelFactory is not None:
        return ChannelFactory.register("viber")(cls)
    return cls


def _validated_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"https", "http"}:
        raise ValueError(f"Unsupported Viber URL scheme: {parsed.scheme or 'missing'}")
    return url


@_register
class ViberAdapter(ChannelBridge):
    """Adapter for Viber via Bot API."""

    async def normalize(self, raw_payload: dict[str, Any]) -> NormalizedMessage:
        sender = raw_payload.get("sender", {})
        message = raw_payload.get("message", {})
        return NormalizedMessage(
            id=raw_payload.get("message_token", str(raw_payload.get("timestamp", ""))),
            channel="viber",
            sender_id=sender.get("id", ""),
            sender_name=sender.get("name", ""),
            text=message.get("text", ""),
            timestamp=float(raw_payload.get("timestamp", time.time() * 1000)) / 1000.0,
            metadata={
                "event_type": raw_payload.get("event", ""),
                "message_type": message.get("type", ""),
                "avatar": sender.get("avatar", ""),
            },
            raw=raw_payload,
        )

    async def send(self, target_id: str, text: str, **kwargs: Any) -> dict[str, Any]:
        auth_token = self.config.get("viber_auth_token", "")
        sender_name = self.config.get("viber_sender_name", "Bot")
        if not auth_token:
            return {"ok": False, "error": "missing viber_auth_token"}
        url = "https://chatapi.viber.com/pa/send_message"
        payload = json.dumps(
            {
                "receiver": target_id,
                "min_api_version": 1,
                "sender": {"name": sender_name},
                "tracking_data": kwargs.get("tracking_data", ""),
                "type": "text",
                "text": text,
            }
        ).encode()
        req = urllib.request.Request(
            _validated_url(url),
            data=payload,
            headers={
                "X-Viber-Auth-Token": auth_token,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
                result = json.loads(resp.read().decode())
            return {"ok": result.get("status") == 0, **result}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        auth_token = self.config.get("viber_auth_token", "")
        signature = headers.get("X-Viber-Content-Signature", "")
        if not auth_token or not signature:
            return False
        computed = hmac.new(auth_token.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)

    async def connect(self) -> None:
        auth_token = self.config.get("viber_auth_token", "")
        webhook_url = self.config.get("viber_webhook_url", "")
        if not auth_token:
            self.status = ChannelStatus.ERROR
            return
        if webhook_url:
            url = "https://chatapi.viber.com/pa/set_webhook"
            payload = json.dumps(
                {
                    "url": webhook_url,
                    "event_types": ["delivered", "seen", "failed", "message", "conversation_started"],
                }
            ).encode()
            req = urllib.request.Request(
                _validated_url(url),
                data=payload,
                headers={
                    "X-Viber-Auth-Token": auth_token,
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                    result = json.loads(resp.read().decode())
                if result.get("status") == 0:
                    self.status = ChannelStatus.CONNECTED
                else:
                    self.status = ChannelStatus.ERROR
                return
            except Exception:
                self.status = ChannelStatus.ERROR
                return
        # No webhook URL configured -- just verify account info
        url = "https://chatapi.viber.com/pa/get_account_info"
        req = urllib.request.Request(
            _validated_url(url),
            data=b"{}",
            headers={
                "X-Viber-Auth-Token": auth_token,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                result = json.loads(resp.read().decode())
            if result.get("status") == 0:
                self.status = ChannelStatus.CONNECTED
            else:
                self.status = ChannelStatus.ERROR
        except Exception:
            self.status = ChannelStatus.ERROR

    async def disconnect(self) -> None:
        auth_token = self.config.get("viber_auth_token", "")
        if auth_token:
            url = "https://chatapi.viber.com/pa/set_webhook"
            payload = json.dumps({"url": ""}).encode()
            req = urllib.request.Request(
                _validated_url(url),
                data=payload,
                headers={
                    "X-Viber-Auth-Token": auth_token,
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                urllib.request.urlopen(req, timeout=10)  # nosec B310
            except Exception:
                pass
        self.status = ChannelStatus.DISCONNECTED
