"""WhatsApp channel adapter."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.request
from typing import Any

from python.helpers.channel_bridge import ChannelBridge, ChannelStatus, NormalizedMessage

try:
    from python.helpers.channel_factory import ChannelFactory
except ImportError:  # pragma: no cover
    ChannelFactory = None  # type: ignore[assignment,misc]


def _register(cls: type) -> type:
    if ChannelFactory is not None:
        return ChannelFactory.register("whatsapp")(cls)
    return cls


@_register
class WhatsAppAdapter(ChannelBridge):
    """Adapter for the WhatsApp Business API."""

    async def normalize(self, raw_payload: dict[str, Any]) -> NormalizedMessage:
        entry = (raw_payload.get("entry", [{}]) or [{}])[0]
        changes = (entry.get("changes", [{}]) or [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [{}])
        msg = messages[0] if messages else {}
        contacts = value.get("contacts", [{}])
        contact = contacts[0] if contacts else {}

        return NormalizedMessage(
            id=msg.get("id", ""),
            channel="whatsapp",
            sender_id=msg.get("from", ""),
            sender_name=contact.get("profile", {}).get("name", ""),
            text=msg.get("text", {}).get("body", "") if isinstance(msg.get("text"), dict) else msg.get("text", ""),
            timestamp=float(msg.get("timestamp", time.time())),
            metadata={
                "phone_number_id": value.get("metadata", {}).get("phone_number_id", ""),
                "message_type": msg.get("type", "text"),
            },
            raw=raw_payload,
        )

    async def send(self, target_id: str, text: str, **kwargs: Any) -> dict[str, Any]:
        access_token = self.config.get("whatsapp_access_token", "")
        phone_number_id = self.config.get("whatsapp_phone_number_id", "")
        api_version = self.config.get("whatsapp_api_version", "v17.0")
        if not access_token or not phone_number_id:
            return {"ok": False, "error": "missing whatsapp_access_token or whatsapp_phone_number_id"}
        url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
        payload = json.dumps({
            "messaging_product": "whatsapp",
            "to": target_id,
            "type": "text",
            "text": {"body": text},
        }).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
            return {"ok": True, **result}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        app_secret = self.config.get("app_secret", "")
        signature = headers.get("X-Hub-Signature-256", "")
        if not all([app_secret, signature]):
            return False
        try:
            expected = "sha256=" + hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, signature)
        except Exception:
            return False

    async def connect(self) -> None:
        access_token = self.config.get("whatsapp_access_token", "")
        phone_number_id = self.config.get("whatsapp_phone_number_id", "")
        api_version = self.config.get("whatsapp_api_version", "v17.0")
        if not access_token or not phone_number_id:
            self.status = ChannelStatus.ERROR
            return
        url = f"https://graph.facebook.com/{api_version}/{phone_number_id}"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    self.status = ChannelStatus.CONNECTED
                else:
                    self.status = ChannelStatus.ERROR
        except Exception:
            self.status = ChannelStatus.ERROR

    async def disconnect(self) -> None:
        self.status = ChannelStatus.DISCONNECTED
