"""Microsoft Teams channel adapter."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.request
import urllib.parse
from typing import Any

from python.helpers.channel_bridge import ChannelBridge, ChannelStatus, NormalizedMessage

try:
    from python.helpers.channel_factory import ChannelFactory
except ImportError:  # pragma: no cover
    ChannelFactory = None  # type: ignore[assignment,misc]

_TOKEN_URL = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"


def _register(cls: type) -> type:
    if ChannelFactory is not None:
        return ChannelFactory.register("teams")(cls)
    return cls


@_register
class TeamsAdapter(ChannelBridge):
    """Adapter for Microsoft Teams via Bot Framework."""

    _access_token: str | None = None

    async def normalize(self, raw_payload: dict[str, Any]) -> NormalizedMessage:
        from_user = raw_payload.get("from", {})
        conversation = raw_payload.get("conversation", {})
        return NormalizedMessage(
            id=raw_payload.get("id", ""),
            channel="teams",
            sender_id=from_user.get("id", ""),
            sender_name=from_user.get("name", ""),
            text=raw_payload.get("text", ""),
            timestamp=float(raw_payload.get("timestamp", time.time())),
            metadata={
                "conversation_id": conversation.get("id", ""),
                "tenant_id": conversation.get("tenantId", ""),
                "activity_type": raw_payload.get("type", ""),
            },
            raw=raw_payload,
        )

    async def send(self, target_id: str, text: str, **kwargs: Any) -> dict[str, Any]:
        service_url = self.config.get("teams_service_url", "https://smba.trafficmanager.net/amer")
        url = f"{service_url.rstrip('/')}/v3/conversations/{target_id}/activities"
        payload = json.dumps({"type": "message", "text": text}).encode()
        headers = {
            "Authorization": f"Bearer {self._access_token or ''}",
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:  # nosec B310 - configured Bot Framework URL
                data = json.loads(resp.read().decode())
                return {"ok": True, "id": data.get("id", "")}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        auth_header = headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return False

        # HMAC verification when a shared secret is configured
        shared_secret = self.config.get("teams_shared_secret", "")
        if shared_secret:
            signature = headers.get("X-Teams-Signature", "")
            if not signature:
                return False
            try:
                computed = hmac.new(
                    shared_secret.encode(), body, hashlib.sha256
                ).hexdigest()
                return hmac.compare_digest(computed, signature)
            except Exception:
                return False

        # Basic Bearer token presence check (JWT validation against Microsoft
        # OpenID metadata should be done in production with a dedicated library)
        return True

    async def connect(self) -> None:
        app_id = self.config.get("teams_app_id", "")
        app_password = self.config.get("teams_app_password", "")
        if not app_id or not app_password:
            self.status = ChannelStatus.ERROR
            return

        form_data = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": app_id,
            "client_secret": app_password,
            "scope": "https://api.botframework.com/.default",
        }).encode()
        req = urllib.request.Request(
            _TOKEN_URL, data=form_data, method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:  # nosec B310 - Microsoft OAuth endpoint
                data = json.loads(resp.read().decode())
                self._access_token = data.get("access_token", "")
            self.status = ChannelStatus.CONNECTED
        except Exception:
            self.status = ChannelStatus.ERROR

    async def disconnect(self) -> None:
        self._access_token = None
        self.status = ChannelStatus.DISCONNECTED
