"""IRC channel adapter."""

from __future__ import annotations

import socket
import ssl
import time
from typing import Any

from python.helpers.channel_bridge import ChannelBridge, ChannelStatus, NormalizedMessage

try:
    from python.helpers.channel_factory import ChannelFactory
except ImportError:  # pragma: no cover
    ChannelFactory = None  # type: ignore[assignment,misc]


def _register(cls: type) -> type:
    if ChannelFactory is not None:
        return ChannelFactory.register("irc")(cls)
    return cls


@_register
class IrcAdapter(ChannelBridge):
    """Adapter for IRC using the irc library."""

    async def normalize(self, raw_payload: dict[str, Any]) -> NormalizedMessage:
        return NormalizedMessage(
            id=raw_payload.get("id", ""),
            channel="irc",
            sender_id=raw_payload.get("nick", ""),
            sender_name=raw_payload.get("nick", ""),
            text=raw_payload.get("text", raw_payload.get("message", "")),
            timestamp=float(raw_payload.get("timestamp", time.time())),
            metadata={
                "irc_channel": raw_payload.get("channel", ""),
                "command": raw_payload.get("command", "PRIVMSG"),
                "host": raw_payload.get("host", ""),
            },
            raw=raw_payload,
        )

    def _send_raw(self, line: str) -> None:
        """Send a raw IRC line over the socket."""
        if hasattr(self, "_sock") and self._sock:
            self._sock.sendall(f"{line}\r\n".encode("utf-8"))

    async def send(self, target_id: str, text: str, **kwargs: Any) -> dict[str, Any]:
        if not hasattr(self, "_sock") or not self._sock:
            return {"ok": False, "error": "not connected to IRC server"}
        try:
            # Split long messages to stay within IRC 512-byte line limit
            for line in text.split("\n"):
                self._send_raw(f"PRIVMSG {target_id} :{line}")
            return {"ok": True, "target": target_id, "text": text}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        # IRC does not use webhooks; messages arrive via persistent socket.
        return True

    async def connect(self) -> None:
        server = self.config.get("irc_server", "")
        port = int(self.config.get("irc_port", 6667))
        use_ssl = self.config.get("irc_ssl", False)
        nickname = self.config.get("irc_nickname", "agent-jumbo")
        password = self.config.get("irc_password", "")
        channels = self.config.get("irc_channels", [])
        if not server:
            self.status = ChannelStatus.ERROR
            return
        try:
            sock = socket.create_connection((server, port), timeout=10)
            if use_ssl:
                ctx = ssl.create_default_context()
                sock = ctx.wrap_socket(sock, server_hostname=server)
            self._sock = sock
            if password:
                self._send_raw(f"PASS {password}")
            self._send_raw(f"NICK {nickname}")
            self._send_raw(f"USER {nickname} 0 * :{nickname}")
            # Wait briefly for server welcome
            sock.settimeout(5)
            try:
                data = sock.recv(4096).decode("utf-8", errors="replace")
                # Respond to PING during connection handshake
                for line in data.split("\r\n"):
                    if line.startswith("PING"):
                        self._send_raw(f"PONG {line[5:]}")
            except socket.timeout:
                pass
            # Join configured channels
            if isinstance(channels, str):
                channels = [c.strip() for c in channels.split(",") if c.strip()]
            for channel in channels:
                if not channel.startswith("#"):
                    channel = f"#{channel}"
                self._send_raw(f"JOIN {channel}")
            self.status = ChannelStatus.CONNECTED
        except Exception:
            self.status = ChannelStatus.ERROR

    async def disconnect(self) -> None:
        if hasattr(self, "_sock") and self._sock:
            try:
                self._send_raw("QUIT :Disconnecting")
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        self.status = ChannelStatus.DISCONNECTED
