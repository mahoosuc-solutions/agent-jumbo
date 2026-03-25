"""LINE channel adapter."""

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
        return ChannelFactory.register("line")(cls)
    return cls


def _validated_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"https", "http"}:
        raise ValueError(f"Unsupported LINE URL scheme: {parsed.scheme or 'missing'}")
    return url


@_register
class LineAdapter(ChannelBridge):
    """Adapter for LINE via Messaging API."""

    async def normalize(self, raw_payload: dict[str, Any]) -> NormalizedMessage:
        events = raw_payload.get("events", [])
        event = events[0] if events else raw_payload
        source = event.get("source", {})
        message = event.get("message", {})
        return NormalizedMessage(
            id=message.get("id", ""),
            channel="line",
            sender_id=source.get("userId", ""),
            sender_name=source.get("userId", ""),
            text=message.get("text", ""),
            timestamp=float(event.get("timestamp", time.time() * 1000)) / 1000.0,
            metadata={
                "reply_token": event.get("replyToken", ""),
                "source_type": source.get("type", ""),
                "group_id": source.get("groupId", ""),
                "message_type": message.get("type", ""),
            },
            raw=raw_payload,
        )

    async def send(self, target_id: str, text: str, **kwargs: Any) -> dict[str, Any]:
        access_token = self.config.get("line_channel_access_token", "")
        if not access_token:
            return {"ok": False, "error": "missing line_channel_access_token"}
        # Use reply if reply_token provided, else push
        reply_token = kwargs.get("reply_token", "")
        if reply_token:
            url = "https://api.line.me/v2/bot/message/reply"
            payload = json.dumps(
                {
                    "replyToken": reply_token,
                    "messages": [{"type": "text", "text": text}],
                }
            ).encode()
        else:
            url = "https://api.line.me/v2/bot/message/push"
            payload = json.dumps(
                {
                    "to": target_id,
                    "messages": [{"type": "text", "text": text}],
                }
            ).encode()
        req = urllib.request.Request(
            _validated_url(url),
            data=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
                resp_body = resp.read().decode()
                result = json.loads(resp_body) if resp_body else {}
            return {"ok": True, **result}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        channel_secret = self.config.get("line_channel_secret", "")
        signature = headers.get("X-Line-Signature", "")
        if not channel_secret or not signature:
            return False
        import base64

        digest = hmac.new(channel_secret.encode(), body, hashlib.sha256).digest()
        computed = base64.b64encode(digest).decode()
        return hmac.compare_digest(computed, signature)

    async def connect(self) -> None:
        access_token = self.config.get("line_channel_access_token", "")
        if not access_token:
            self.status = ChannelStatus.ERROR
            return
        url = "https://api.line.me/v2/bot/info"
        req = urllib.request.Request(
            _validated_url(url),
            headers={"Authorization": f"Bearer {access_token}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                if resp.status == 200:
                    self.status = ChannelStatus.CONNECTED
                else:
                    self.status = ChannelStatus.ERROR
        except Exception:
            self.status = ChannelStatus.ERROR

    async def disconnect(self) -> None:
        self.status = ChannelStatus.DISCONNECTED
