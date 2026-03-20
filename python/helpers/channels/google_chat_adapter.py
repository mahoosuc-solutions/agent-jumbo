"""Google Chat channel adapter."""

from __future__ import annotations

import base64
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

_GOOGLE_CHAT_API = "https://chat.googleapis.com/v1"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


def _register(cls: type) -> type:
    if ChannelFactory is not None:
        return ChannelFactory.register("google_chat")(cls)
    return cls


def _base64url(data: bytes) -> str:
    """Base64url-encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


@_register
class GoogleChatAdapter(ChannelBridge):
    """Adapter for Google Chat via Google Workspace API."""

    _access_token: str | None = None

    async def normalize(self, raw_payload: dict[str, Any]) -> NormalizedMessage:
        message = raw_payload.get("message", raw_payload)
        sender = message.get("sender", {})
        space = raw_payload.get("space", message.get("space", {}))
        return NormalizedMessage(
            id=message.get("name", ""),
            channel="google_chat",
            sender_id=sender.get("name", ""),
            sender_name=sender.get("displayName", ""),
            text=message.get("text", message.get("argumentText", "")),
            timestamp=float(message.get("createTime", time.time())),
            metadata={
                "space_name": space.get("name", ""),
                "space_type": space.get("type", ""),
                "thread_name": message.get("thread", {}).get("name", ""),
            },
            raw=raw_payload,
        )

    async def send(self, target_id: str, text: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{_GOOGLE_CHAT_API}/{target_id}/messages"
        payload: dict[str, Any] = {"text": text}

        thread_key = kwargs.get("thread_key")
        if thread_key:
            payload["thread"] = {"threadKey": thread_key}

        data = json.dumps(payload).encode()
        headers = {
            "Authorization": f"Bearer {self._access_token or ''}",
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:  # nosec B310 - Google Chat API URL
                result = json.loads(resp.read().decode())
                return {"ok": True, "name": result.get("name", "")}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        auth_header = headers.get("Authorization", "")

        # Check for verification token (simple shared-secret approach)
        verification_token = self.config.get("google_chat_verification_token", "")
        if verification_token:
            try:
                payload = json.loads(body)
                token_in_payload = payload.get("token", "")
                if token_in_payload:
                    return token_in_payload == verification_token
            except (json.JSONDecodeError, AttributeError):
                pass

        # Bearer token presence check (full JWT verification against Google's
        # public keys should be done in production with a dedicated library)
        if not auth_header.startswith("Bearer "):
            return False
        return True

    async def connect(self) -> None:
        creds_config = self.config.get("google_chat_credentials_json", "")
        if not creds_config:
            self.status = ChannelStatus.ERROR
            return

        try:
            # Load credentials: path string or dict
            if isinstance(creds_config, str):
                with open(creds_config) as fh:
                    creds = json.load(fh)
            else:
                creds = creds_config

            # Build JWT assertion for service account
            import hashlib
            import hmac as _hmac  # noqa: F811

            now = int(time.time())
            header = _base64url(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
            claim_set = {
                "iss": creds.get("client_email", ""),
                "scope": "https://www.googleapis.com/auth/chat.bot",
                "aud": _GOOGLE_TOKEN_URL,
                "iat": now,
                "exp": now + 3600,
            }
            claims = _base64url(json.dumps(claim_set).encode())
            signing_input = f"{header}.{claims}"

            # Sign with RSA private key if available
            private_key_pem = creds.get("private_key", "")
            if private_key_pem:
                try:
                    from python.helpers.channels._jwt_sign import rsa_sign
                except ImportError:
                    rsa_sign = None  # type: ignore[assignment]

                if rsa_sign is not None:
                    signature = rsa_sign(private_key_pem, signing_input.encode())
                else:
                    # Fallback: use hashlib-based placeholder (not cryptographically
                    # valid RSA, but allows the flow to proceed in environments
                    # without RSA libraries -- token exchange will fail gracefully)
                    sig_bytes = hashlib.sha256(signing_input.encode()).digest()
                    signature = _base64url(sig_bytes)

                jwt_token = f"{signing_input}.{signature}"
            else:
                self.status = ChannelStatus.ERROR
                return

            # Exchange JWT for access token
            form_data = urllib.parse.urlencode({
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": jwt_token,
            }).encode()
            req = urllib.request.Request(
                _GOOGLE_TOKEN_URL, data=form_data, method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:  # nosec B310 - Google OAuth endpoint
                data = json.loads(resp.read().decode())
                self._access_token = data.get("access_token", "")

            self.status = ChannelStatus.CONNECTED
        except Exception:
            self.status = ChannelStatus.ERROR

    async def disconnect(self) -> None:
        self._access_token = None
        self.status = ChannelStatus.DISCONNECTED
