"""
MOS (Mahoosuc Operating System) authentication bridge.

Verifies MOS JWT tokens offline and checks product entitlements
via cached HTTP calls to the MOS platform API.
"""

import hashlib
import hmac as hmac_mod
import threading
import time

import jwt
import requests as http_requests

from python.helpers import dotenv

# ── HMAC service-to-service signing ──────────────────────────────────────


def _sign_service_request(path: str) -> dict[str, str]:
    """Generate HMAC-SHA256 headers for authenticated service-to-service calls."""
    secret = dotenv.get_dotenv_value("SERVICE_MESH_SECRET") or ""
    if not secret:
        # Fallback to legacy header when no secret configured
        return {"x-internal-service": "agent-jumbo"}
    timestamp = str(int(time.time()))
    message = f"agent-jumbo|{timestamp}|{path}"
    signature = hmac_mod.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return {
        "x-service-name": "agent-jumbo",
        "x-service-timestamp": timestamp,
        "x-service-signature": signature,
    }


# ── Entitlement cache ─────────────────────────────────────────────────────

_entitlement_cache: dict[str, tuple[bool, float]] = {}
_cache_lock = threading.Lock()
_CACHE_TTL_SECONDS = 300  # 5 minutes


def is_mos_auth_enabled() -> bool:
    """Check if MOS authentication mode is active."""
    return bool(dotenv.get_dotenv_value("MOS_JWT_SECRET"))


def verify_token(token: str) -> dict | None:
    """
    Verify a MOS JWT token offline using the shared secret.

    Returns the decoded payload dict on success, or None on failure.
    Payload contains: userId, email, role, organization_id/organizationId.
    """
    secret = dotenv.get_dotenv_value("MOS_JWT_SECRET")
    if not secret:
        return None

    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        # Normalize organization_id (MOS uses both field names)
        if "organizationId" in payload and "organization_id" not in payload:
            payload["organization_id"] = payload["organizationId"]
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def check_entitlement(organization_id: str, product_key: str = "agent-jumbo") -> bool:
    """
    Check if an organization has an active entitlement for the given product.

    Uses a 5-minute cache to avoid per-request HTTP calls.
    Falls back to True if the MOS API is unreachable (fail-open for availability).
    """
    cache_key = f"{organization_id}:{product_key}"

    with _cache_lock:
        cached = _entitlement_cache.get(cache_key)
        if cached and (time.time() - cached[1]) < _CACHE_TTL_SECONDS:
            return cached[0]

    base_url = dotenv.get_dotenv_value("AIOS_BASE_URL") or "http://127.0.0.1:3000"
    base_url = base_url.rstrip("/")
    url = f"{base_url}/api/platform/entitlements/check"

    try:
        # HMAC-signed service-to-service call
        api_path = f"/api/platform/entitlements/check?product_key={product_key}&organization_id={organization_id}"
        resp = http_requests.get(
            url,
            params={"product_key": product_key, "organization_id": organization_id},
            headers=_sign_service_request(api_path),
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            entitled = data.get("entitled", False)
        else:
            # API error — fail-open to avoid blocking users
            entitled = True
    except Exception:
        # Network error — fail-open
        entitled = True

    with _cache_lock:
        _entitlement_cache[cache_key] = (entitled, time.time())

    return entitled


def extract_token_from_request(flask_request) -> str | None:
    """Extract MOS JWT from Authorization header or cookies."""
    # Check Authorization header
    auth_header = flask_request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    # Check cookies (matching MOS cookie names)
    for cookie_name in ("sAccessToken", "st-access-token", "accessToken"):
        token = flask_request.cookies.get(cookie_name)
        if token:
            return token

    return None


def clear_cache():
    """Clear the entitlement cache (useful for testing)."""
    with _cache_lock:
        _entitlement_cache.clear()
