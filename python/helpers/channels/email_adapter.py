"""Email channel adapter (IMAP/SMTP)."""

from __future__ import annotations

import imaplib
import smtplib
import time
from email.mime.text import MIMEText
from typing import Any

from python.helpers.channel_bridge import ChannelBridge, ChannelStatus, NormalizedMessage

try:
    from python.helpers.channel_factory import ChannelFactory
except ImportError:  # pragma: no cover
    ChannelFactory = None  # type: ignore[assignment,misc]


def _register(cls: type) -> type:
    if ChannelFactory is not None:
        return ChannelFactory.register("email")(cls)
    return cls


@_register
class EmailAdapter(ChannelBridge):
    """Adapter for Email via IMAP (receive) and SMTP (send)."""

    _imap_conn: imaplib.IMAP4_SSL | None = None

    async def normalize(self, raw_payload: dict[str, Any]) -> NormalizedMessage:
        return NormalizedMessage(
            id=raw_payload.get("message_id", ""),
            channel="email",
            sender_id=raw_payload.get("from", ""),
            sender_name=raw_payload.get("from_name", raw_payload.get("from", "")),
            text=raw_payload.get("body", raw_payload.get("text", "")),
            timestamp=float(raw_payload.get("date", time.time())),
            metadata={
                "subject": raw_payload.get("subject", ""),
                "to": raw_payload.get("to", ""),
                "cc": raw_payload.get("cc", ""),
                "in_reply_to": raw_payload.get("in_reply_to", ""),
            },
            raw=raw_payload,
        )

    async def send(self, target_id: str, text: str, **kwargs: Any) -> dict[str, Any]:
        smtp_host = self.config.get("email_smtp_host", "")
        smtp_port = int(self.config.get("email_smtp_port", 587))
        username = self.config.get("email_username", "")
        password = self.config.get("email_password", "")
        from_addr = self.config.get("email_email_address", username)
        subject = kwargs.get("subject", "Notification")

        msg = MIMEText(text)
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = target_id

        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
                server.starttls()
                server.login(username, password)
                server.sendmail(from_addr, [target_id], msg.as_string())
                msg_id = msg.get("Message-ID", "")
            return {"ok": True, "message_id": msg_id}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        # Email does not use webhooks; IMAP polling is used instead.
        return True

    async def connect(self) -> None:
        smtp_host = self.config.get("email_smtp_host", "")
        smtp_port = int(self.config.get("email_smtp_port", 587))
        username = self.config.get("email_username", "")
        password = self.config.get("email_password", "")

        if not smtp_host or not username:
            self.status = ChannelStatus.ERROR
            return

        try:
            # Test SMTP connectivity
            with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
                server.starttls()
                server.login(username, password)

            # Optionally test IMAP connectivity
            imap_host = self.config.get("email_imap_host", "")
            if imap_host:
                conn = imaplib.IMAP4_SSL(imap_host, timeout=20)
                imap_user = self.config.get("email_imap_username", username)
                imap_pass = self.config.get("email_imap_password", password)
                conn.login(imap_user, imap_pass)
                self._imap_conn = conn

            self.status = ChannelStatus.CONNECTED
        except Exception:
            self.status = ChannelStatus.ERROR

    async def disconnect(self) -> None:
        if self._imap_conn is not None:
            try:
                self._imap_conn.logout()
            except Exception:
                pass
            self._imap_conn = None
        self.status = ChannelStatus.DISCONNECTED
