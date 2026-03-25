"""Twilio SMS channel adapter."""

from __future__ import annotations

import base64
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
        return ChannelFactory.register("twilio_sms")(cls)
    return cls


def _validated_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"https", "http"}:
        raise ValueError(f"Unsupported Twilio URL scheme: {parsed.scheme or 'missing'}")
    return url


@_register
class TwilioSmsAdapter(ChannelBridge):
    """Adapter for Twilio SMS via REST API."""

    async def normalize(self, raw_payload: dict[str, Any]) -> NormalizedMessage:
        return NormalizedMessage(
            id=raw_payload.get("MessageSid", ""),
            channel="twilio_sms",
            sender_id=raw_payload.get("From", ""),
            sender_name=raw_payload.get("From", ""),
            text=raw_payload.get("Body", ""),
            timestamp=time.time(),
            metadata={
                "to": raw_payload.get("To", ""),
                "num_media": raw_payload.get("NumMedia", "0"),
                "sms_status": raw_payload.get("SmsStatus", ""),
            },
            raw=raw_payload,
        )

    async def send(self, target_id: str, text: str, **kwargs: Any) -> dict[str, Any]:
        account_sid = self.config.get("twilio_account_sid", "")
        auth_token = self.config.get("twilio_auth_token", "")
        from_number = self.config.get("twilio_from_number", "")
        if not all([account_sid, auth_token, from_number]):
            return {"ok": False, "error": "missing twilio_account_sid, twilio_auth_token, or twilio_from_number"}
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        payload = urllib.parse.urlencode(
            {
                "To": target_id,
                "From": from_number,
                "Body": text,
            }
        ).encode()
        # Twilio uses HTTP Basic Auth
        credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
        req = urllib.request.Request(
            _validated_url(url),
            data=payload,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
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
        auth_token = self.config.get("twilio_auth_token", "")
        signature = headers.get("X-Twilio-Signature", "")
        webhook_url = self.config.get("twilio_webhook_url", "")
        if not all([auth_token, signature, webhook_url]):
            return False
        try:
            # Parse form-encoded body and sort params
            params = urllib.parse.parse_qs(body.decode(), keep_blank_values=True)
            # Twilio expects single values; build sorted key=value string
            sorted_params = sorted(params.items())
            param_string = "".join(k + v[0] for k, v in sorted_params)
            data = (webhook_url + param_string).encode()
            computed = base64.b64encode(hmac.new(auth_token.encode(), data, hashlib.sha1).digest()).decode()
            return hmac.compare_digest(computed, signature)
        except Exception:
            return False

    async def connect(self) -> None:
        account_sid = self.config.get("twilio_account_sid", "")
        auth_token = self.config.get("twilio_auth_token", "")
        if not account_sid or not auth_token:
            self.status = ChannelStatus.ERROR
            return
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}.json"
        credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
        req = urllib.request.Request(
            _validated_url(url),
            headers={"Authorization": f"Basic {credentials}"},
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
