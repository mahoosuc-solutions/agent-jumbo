"""Mastodon channel adapter."""

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
        return ChannelFactory.register("mastodon")(cls)
    return cls


@_register
class MastodonAdapter(ChannelBridge):
    """Adapter for Mastodon via Mastodon.py / REST API."""

    async def normalize(self, raw_payload: dict[str, Any]) -> NormalizedMessage:
        account = raw_payload.get("account", {})
        return NormalizedMessage(
            id=str(raw_payload.get("id", "")),
            channel="mastodon",
            sender_id=str(account.get("id", "")),
            sender_name=account.get("username", account.get("acct", "")),
            text=raw_payload.get("content", ""),
            timestamp=float(raw_payload.get("created_at_epoch", time.time())),
            metadata={
                "visibility": raw_payload.get("visibility", ""),
                "in_reply_to_id": raw_payload.get("in_reply_to_id", ""),
                "url": raw_payload.get("url", ""),
                "spoiler_text": raw_payload.get("spoiler_text", ""),
            },
            raw=raw_payload,
        )

    async def send(self, target_id: str, text: str, **kwargs: Any) -> dict[str, Any]:
        instance_url = self.config.get("mastodon_instance_url", "").rstrip("/")
        access_token = self.config.get("mastodon_access_token", "")
        if not instance_url or not access_token:
            return {"ok": False, "error": "missing mastodon_instance_url or mastodon_access_token"}
        url = f"{instance_url}/api/v1/statuses"
        visibility = kwargs.get("visibility", "direct")
        form_data = urllib.parse.urlencode({
            "status": text,
            "visibility": visibility,
            "in_reply_to_id": target_id or "",
        }).encode()
        req = urllib.request.Request(
            url,
            data=form_data,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/x-www-form-urlencoded",
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
        # Mastodon streaming uses WebSockets; webhook verification is optional.
        secret = self.config.get("mastodon_webhook_secret", "")
        if not secret:
            return True
        signature = headers.get("X-Hub-Signature", "")
        if not signature:
            return False
        computed = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)

    async def connect(self) -> None:
        instance_url = self.config.get("mastodon_instance_url", "").rstrip("/")
        access_token = self.config.get("mastodon_access_token", "")
        if not instance_url or not access_token:
            self.status = ChannelStatus.ERROR
            return
        url = f"{instance_url}/api/v1/accounts/verify_credentials"
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
