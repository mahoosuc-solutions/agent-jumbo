"""Rocket.Chat channel adapter."""

from __future__ import annotations

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
        return ChannelFactory.register("rocketchat")(cls)
    return cls


def _validated_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"https", "http"}:
        raise ValueError(f"Unsupported Rocket.Chat URL scheme: {parsed.scheme or 'missing'}")
    return url


@_register
class RocketChatAdapter(ChannelBridge):
    """Adapter for Rocket.Chat via REST API."""

    async def normalize(self, raw_payload: dict[str, Any]) -> NormalizedMessage:
        msg = raw_payload.get("message", raw_payload) if "message" in raw_payload else raw_payload
        user = msg.get("u", {})
        return NormalizedMessage(
            id=msg.get("_id", ""),
            channel="rocketchat",
            sender_id=user.get("_id", ""),
            sender_name=user.get("username", user.get("name", "")),
            text=msg.get("msg", ""),
            timestamp=float(msg.get("ts", {}).get("$date", time.time() * 1000)) / 1000.0
            if isinstance(msg.get("ts"), dict)
            else time.time(),
            metadata={
                "rid": msg.get("rid", ""),
                "channel_name": raw_payload.get("channel_name", ""),
                "msg_type": msg.get("t", ""),
            },
            raw=raw_payload,
        )

    async def send(self, target_id: str, text: str, **kwargs: Any) -> dict[str, Any]:
        base_url = self.config.get("rocketchat_url", "").rstrip("/")
        auth_token = self.config.get("rocketchat_auth_token", "")
        user_id = self.config.get("rocketchat_user_id", "")
        if not all([base_url, auth_token, user_id]):
            return {"ok": False, "error": "missing rocketchat_url, rocketchat_auth_token, or rocketchat_user_id"}
        url = f"{base_url}/api/v1/chat.sendMessage"
        payload = json.dumps(
            {
                "message": {
                    "rid": target_id,
                    "msg": text,
                },
            }
        ).encode()
        req = urllib.request.Request(
            _validated_url(url),
            data=payload,
            headers={
                "X-Auth-Token": auth_token,
                "X-User-Id": user_id,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
                result = json.loads(resp.read().decode())
            return {"ok": result.get("success", False), **result}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        token = self.config.get("rocketchat_webhook_token", "")
        if not token:
            return False  # fail-closed: require rocketchat_webhook_token
        header_token = headers.get("X-Rocketchat-Token", "")
        return hmac.compare_digest(token, header_token)

    async def connect(self) -> None:
        base_url = self.config.get("rocketchat_url", "").rstrip("/")
        auth_token = self.config.get("rocketchat_auth_token", "")
        user_id = self.config.get("rocketchat_user_id", "")
        if not all([base_url, auth_token, user_id]):
            self.status = ChannelStatus.ERROR
            return
        url = f"{base_url}/api/v1/me"
        req = urllib.request.Request(
            _validated_url(url),
            headers={
                "X-Auth-Token": auth_token,
                "X-User-Id": user_id,
            },
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
