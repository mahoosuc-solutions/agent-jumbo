"""Discord channel adapter."""

from __future__ import annotations

import time
from typing import Any

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from python.helpers.channel_bridge import ChannelBridge, ChannelStatus, NormalizedMessage

try:
    from python.helpers.channel_factory import ChannelFactory
except ImportError:  # pragma: no cover
    ChannelFactory = None  # type: ignore[assignment,misc]


def _register(cls: type) -> type:
    if ChannelFactory is not None:
        return ChannelFactory.register("discord")(cls)
    return cls


@_register
class DiscordAdapter(ChannelBridge):
    """Adapter for the Discord messaging platform."""

    async def normalize(self, raw_payload: dict[str, Any]) -> NormalizedMessage:
        data = raw_payload
        author = data.get("author", {})
        return NormalizedMessage(
            id=data.get("id", ""),
            channel="discord",
            sender_id=author.get("id", ""),
            sender_name=author.get("username", ""),
            text=data.get("content", ""),
            timestamp=time.time(),
            metadata={"guild_id": data.get("guild_id", "")},
            raw=raw_payload,
        )

    async def send(self, target_id: str, text: str, **kwargs: Any) -> dict[str, Any]:
        # Placeholder -- real implementation would use discord.py or REST API
        return {"channel_id": target_id, "content": text, "sent": True}

    async def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        public_key_hex = self.config.get("public_key", "")
        signature_hex = headers.get("X-Signature-Ed25519", "")
        timestamp = headers.get("X-Signature-Timestamp", "")
        if not all([public_key_hex, signature_hex, timestamp]):
            return False
        try:
            verify_key = VerifyKey(bytes.fromhex(public_key_hex))
            message = timestamp.encode() + body
            verify_key.verify(message, bytes.fromhex(signature_hex))
            return True
        except (BadSignatureError, Exception):
            return False

    async def connect(self) -> None:
        self.status = ChannelStatus.CONNECTED

    async def disconnect(self) -> None:
        self.status = ChannelStatus.DISCONNECTED
