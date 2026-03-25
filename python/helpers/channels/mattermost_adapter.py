"""Mattermost channel adapter."""

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
        return ChannelFactory.register("mattermost")(cls)
    return cls


def _validated_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"https", "http"}:
        raise ValueError(f"Unsupported Mattermost URL scheme: {parsed.scheme or 'missing'}")
    return url


@_register
class MattermostAdapter(ChannelBridge):
    """Adapter for Mattermost via REST API."""

    async def normalize(self, raw_payload: dict[str, Any]) -> NormalizedMessage:
        post = raw_payload.get("post", raw_payload)
        if isinstance(post, str):
            import json

            try:
                post = json.loads(post)
            except (json.JSONDecodeError, TypeError):
                post = raw_payload
        return NormalizedMessage(
            id=post.get("id", ""),
            channel="mattermost",
            sender_id=post.get("user_id", ""),
            sender_name=raw_payload.get("user_name", post.get("user_id", "")),
            text=post.get("message", ""),
            timestamp=float(post.get("create_at", time.time() * 1000)) / 1000.0,
            metadata={
                "channel_id": post.get("channel_id", ""),
                "team_id": raw_payload.get("team_id", ""),
                "trigger_word": raw_payload.get("trigger_word", ""),
            },
            raw=raw_payload,
        )

    async def send(self, target_id: str, text: str, **kwargs: Any) -> dict[str, Any]:
        base_url = self.config.get("mattermost_url", "").rstrip("/")
        token = self.config.get("mattermost_token", "")
        if not base_url or not token:
            return {"ok": False, "error": "missing mattermost_url or mattermost_token"}
        url = f"{base_url}/api/v4/posts"
        payload = json.dumps(
            {
                "channel_id": target_id,
                "message": text,
            }
        ).encode()
        req = urllib.request.Request(
            _validated_url(url),
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
                result = json.loads(resp.read().decode())
            return {"ok": True, **result}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        token = self.config.get("mattermost_webhook_token", "")
        if not token:
            return False  # fail-closed: require mattermost_webhook_token
        # Mattermost outgoing webhooks include a token field in the payload
        try:
            payload = json.loads(body)
            return hmac.compare_digest(token, payload.get("token", ""))
        except Exception:
            return False

    async def connect(self) -> None:
        base_url = self.config.get("mattermost_url", "").rstrip("/")
        token = self.config.get("mattermost_token", "")
        if not base_url or not token:
            self.status = ChannelStatus.ERROR
            return
        url = f"{base_url}/api/v4/users/me"
        req = urllib.request.Request(
            _validated_url(url),
            headers={"Authorization": f"Bearer {token}"},
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
