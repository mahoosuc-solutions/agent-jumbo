"""Credential store for payment provider API keys and secrets.

Writes credentials to the local .env file and optionally to Vercel
environment variables via the Vercel CLI.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Mapping from logical credential name → environment variable name
PROVIDER_ENV_MAP: dict[str, dict[str, str]] = {
    "stripe": {
        "stripe_secret_key": "STRIPE_API_KEY",  # pragma: allowlist secret
        "stripe_webhook_secret": "STRIPE_WEBHOOK_SECRET",  # pragma: allowlist secret
    },
    "square": {
        "square_application_id": "SQUARE_APPLICATION_ID",
        "square_application_secret": "SQUARE_ACCESS_TOKEN",  # pragma: allowlist secret
        "square_webhook_signature_key": "SQUARE_WEBHOOK_SIGNATURE_KEY",  # pragma: allowlist secret
    },
    "paypal": {
        "paypal_client_id": "PAYPAL_CLIENT_ID",
        "paypal_client_secret": "PAYPAL_CLIENT_SECRET",  # pragma: allowlist secret
        "paypal_webhook_id": "PAYPAL_WEBHOOK_ID",
    },
}


class CredentialStore:
    """Persists payment provider credentials locally and optionally to Vercel."""

    def __init__(self, env_path: str | None = None):
        self.env_path = env_path or os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")

    def write_credentials(
        self,
        provider: str,
        credentials: dict[str, str],
        push_to_vercel: bool = False,
    ) -> dict[str, str]:
        """Write credentials for a provider.

        Args:
            provider: Provider name (``"stripe"``, ``"square"``, ``"paypal"``).
            credentials: Dict of logical field names → values (e.g. ``{"stripe_secret_key": "sk_test_..."}``)
            push_to_vercel: If True, attempt to push to Vercel via CLI.

        Returns:
            Dict of env var names written → values (values are redacted in the return for logging safety).
        """
        env_map = PROVIDER_ENV_MAP.get(provider, {})
        written: dict[str, str] = {}

        for logical_name, value in credentials.items():
            if not value:
                continue
            env_name = env_map.get(logical_name, logical_name.upper())
            self._write_to_env_file(env_name, value)
            written[env_name] = f"{value[:8]}..." if len(value) > 8 else "***"

            if push_to_vercel:
                self._push_to_vercel(env_name, value)

        return written

    def read_credential(self, env_name: str) -> str | None:
        """Read a credential from the environment or .env file."""
        return os.environ.get(env_name) or self._read_from_env_file(env_name)

    def list_configured_providers(self) -> dict[str, bool]:
        """Return which providers have their required credentials configured."""
        return {
            "stripe": bool(self.read_credential("STRIPE_API_KEY") and self.read_credential("STRIPE_WEBHOOK_SECRET")),
            "square": bool(
                self.read_credential("SQUARE_APPLICATION_ID") and self.read_credential("SQUARE_ACCESS_TOKEN")
            ),
            "paypal": bool(self.read_credential("PAYPAL_CLIENT_ID") and self.read_credential("PAYPAL_CLIENT_SECRET")),
        }

    # -- internal helpers ----------------------------------------------------

    def _write_to_env_file(self, key: str, value: str) -> None:
        env_file = Path(self.env_path)
        if env_file.exists():
            lines = env_file.read_text().splitlines()
        else:
            lines = []

        new_line = f'{key}="{value}"'
        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
                lines[i] = new_line
                updated = True
                break

        if not updated:
            lines.append(new_line)

        env_file.write_text("\n".join(lines) + "\n")
        logger.info("Wrote %s to %s", key, self.env_path)

    def _read_from_env_file(self, key: str) -> str | None:
        env_file = Path(self.env_path)
        if not env_file.exists():
            return None
        for line in env_file.read_text().splitlines():
            if line.startswith(f"{key}="):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                return value or None
        return None

    def _push_to_vercel(self, key: str, value: str) -> None:
        try:
            result = subprocess.run(
                ["vercel", "env", "add", key, "production"],
                input=value,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                logger.info("Pushed %s to Vercel production env", key)
            else:
                logger.warning("vercel env add %s failed: %s", key, result.stderr)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.warning("Could not push %s to Vercel: %s", key, exc)
