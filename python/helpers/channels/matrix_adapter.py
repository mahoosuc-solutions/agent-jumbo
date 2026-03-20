"""Matrix channel adapter."""

from __future__ import annotations

import hmac
import json
import time
import urllib.request
import uuid
from typing import Any

from python.helpers.channel_bridge import ChannelBridge, ChannelStatus, NormalizedMessage

try:
    from python.helpers.channel_factory import ChannelFactory
except ImportError:  # pragma: no cover
    ChannelFactory = None  # type: ignore[assignment,misc]


def _register(cls: type) -> type:
    if ChannelFactory is not None:
        return ChannelFactory.register("matrix")(cls)
    return cls


@_register
class MatrixAdapter(ChannelBridge):
    """Adapter for Matrix via Client-Server API."""

    async def normalize(self, raw_payload: dict[str, Any]) -> NormalizedMessage:
        content = raw_payload.get("content", {})
        return NormalizedMessage(
            id=raw_payload.get("event_id", ""),
            channel="matrix",
            sender_id=raw_payload.get("sender", ""),
            sender_name=raw_payload.get("sender", ""),
            text=content.get("body", ""),
            timestamp=float(raw_payload.get("origin_server_ts", time.time() * 1000)) / 1000.0,
            metadata={
                "room_id": raw_payload.get("room_id", ""),
                "event_type": raw_payload.get("type", ""),
                "msgtype": content.get("msgtype", ""),
            },
            raw=raw_payload,
        )

    async def send(self, target_id: str, text: str, **kwargs: Any) -> dict[str, Any]:
        homeserver = self.config.get("matrix_homeserver_url", "").rstrip("/")
        access_token = self.config.get("matrix_access_token", "")
        if not homeserver or not access_token:
            return {"ok": False, "error": "missing matrix_homeserver_url or matrix_access_token"}
        txn_id = uuid.uuid4().hex
        room_id = urllib.request.quote(target_id, safe="")
        url = f"{homeserver}/_matrix/client/v3/rooms/{room_id}/send/m.room.message/{txn_id}"
        msgtype = kwargs.get("msgtype", "m.text")
        payload = json.dumps({
            "msgtype": msgtype,
            "body": text,
        }).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="PUT",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
            return {"ok": True, **result}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        # Matrix Application Services use hs_token for authentication
        hs_token = self.config.get("matrix_hs_token", "")
        if not hs_token:
            return True
        auth = headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return hmac.compare_digest(hs_token, auth[7:])
        return False

    async def connect(self) -> None:
        homeserver = self.config.get("matrix_homeserver_url", "").rstrip("/")
        access_token = self.config.get("matrix_access_token", "")
        if not homeserver or not access_token:
            self.status = ChannelStatus.ERROR
            return
        url = f"{homeserver}/_matrix/client/v3/account/whoami"
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
