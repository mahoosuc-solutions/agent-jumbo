"""
Usage enforcement for Agent Jumbo subscription tiers.

Tracks operation counts per organization and enforces tier limits.
Limits are fetched from MOS and cached. Counts are stored in Redis
when available, falling back to in-memory.
"""

import logging
import threading
import time

import requests as http_requests

from python.helpers import dotenv
from python.helpers.mos_auth import _sign_service_request

# ── Redis client (lazy init) ─────────────────────────────────────────

_redis_client = None
_redis_init_attempted = False


def _get_redis():
    """Get Redis client for usage counters. Returns None if unavailable."""
    global _redis_client, _redis_init_attempted
    if _redis_init_attempted:
        return _redis_client
    _redis_init_attempted = True
    redis_url = dotenv.get_dotenv_value("REDIS_URL") or ""
    if not redis_url:
        return None
    try:
        import redis

        _redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
        _redis_client.ping()
        logging.info("[usage] Redis connected for usage counters")
        return _redis_client
    except Exception as e:
        logging.warning(f"[usage] Redis unavailable, using in-memory counters: {e}")
        _redis_client = None
        return None


# ── Tier limit cache ──────────────────────────────────────────────────

_limits_cache: dict[str, dict] = {}
_limits_lock = threading.Lock()
_LIMITS_CACHE_TTL = 300  # 5 minutes

# ── Operation counters (in-memory fallback, keyed by org:month) ───────

_counters: dict[str, int] = {}
_counters_lock = threading.Lock()
_REDIS_COUNTER_PREFIX = "usage:"
_REDIS_COUNTER_TTL = 3888000  # 45 days


def _current_month_key(org_id: str) -> str:
    """Generate a counter key for the current month."""
    month = time.strftime("%Y-%m")
    return f"{org_id}:{month}"


def _get_cached_limits(org_id: str) -> dict | None:
    """Get cached tier limits for an org."""
    with _limits_lock:
        entry = _limits_cache.get(org_id)
        if entry and (time.time() - entry.get("_fetched_at", 0)) < _LIMITS_CACHE_TTL:
            return entry
    return None


def _fetch_limits_from_mos(org_id: str) -> dict:
    """Fetch tier limits from the MOS platform API."""
    base_url = dotenv.get_dotenv_value("AIOS_BASE_URL") or "http://127.0.0.1:3000"
    url = f"{base_url.rstrip('/')}/api/platform/entitlements/check"

    try:
        resp = http_requests.get(
            url,
            params={"product_key": "agent-jumbo", "organization_id": org_id},
            headers=_sign_service_request(
                f"/api/platform/entitlements/check?product_key=agent-jumbo&organization_id={org_id}"
            ),
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            limits = {
                "entitled": data.get("entitled", False),
                "entitlement_status": data.get("entitlement_status", "disabled"),
                "_fetched_at": time.time(),
            }
            # Also fetch tier-specific limits if available
            try:
                sub_resp = http_requests.get(
                    f"{base_url.rstrip('/')}/api/platform/subscription-tier",
                    params={"organization_id": org_id},
                    headers=_sign_service_request(f"/api/platform/subscription-tier?organization_id={org_id}"),
                    timeout=5,
                )
                if sub_resp.status_code == 200:
                    tier_data = sub_resp.json()
                    limits["tier"] = tier_data.get("tier", "free")
                    limits["limits"] = tier_data.get("limits", {})
            except Exception:
                pass

            with _limits_lock:
                _limits_cache[org_id] = limits
            return limits
    except Exception:
        pass

    # Fail-open: return unlimited on error
    return {"entitled": True, "tier": "unknown", "_fetched_at": time.time()}


# ── Default tier limits (used when MOS is unreachable) ────────────────

DEFAULT_TIER_LIMITS = {
    "free": {"operations_monthly": 100},
    "starter": {"operations_monthly": 500},
    "professional": {"operations_monthly": 5000},
    "business": {"operations_monthly": 25000},
    "enterprise": {"operations_monthly": -1},  # unlimited
}


def get_operation_limit(org_id: str) -> int:
    """Get the monthly operation limit for an organization. Returns -1 for unlimited."""
    limits = _get_cached_limits(org_id) or _fetch_limits_from_mos(org_id)
    tier = limits.get("tier", "free")
    tier_limits = limits.get("limits", {})

    # Try MOS-provided limits first, fall back to defaults
    ops_limit = tier_limits.get("max_operations", tier_limits.get("operations_monthly"))
    if ops_limit is not None:
        return int(ops_limit)
    return DEFAULT_TIER_LIMITS.get(tier, DEFAULT_TIER_LIMITS["free"]).get("operations_monthly", 100)


def get_current_usage(org_id: str) -> int:
    """Get the current month's operation count for an organization."""
    key = _current_month_key(org_id)
    r = _get_redis()
    if r:
        try:
            val = r.get(f"{_REDIS_COUNTER_PREFIX}{key}")
            return int(val) if val else 0
        except Exception:
            pass
    # Fallback to in-memory
    with _counters_lock:
        return _counters.get(key, 0)


def increment_usage(org_id: str, count: int = 1) -> int:
    """Increment the operation counter. Returns the new total."""
    key = _current_month_key(org_id)
    r = _get_redis()
    if r:
        try:
            redis_key = f"{_REDIS_COUNTER_PREFIX}{key}"
            new_val = r.incrby(redis_key, count)
            # Set TTL on first increment (only if no TTL yet)
            if new_val == count:
                r.expire(redis_key, _REDIS_COUNTER_TTL)
            # Write-through to in-memory cache
            with _counters_lock:
                _counters[key] = new_val
            return new_val
        except Exception:
            pass
    # Fallback to in-memory only
    with _counters_lock:
        _counters[key] = _counters.get(key, 0) + count
        return _counters[key]


def check_usage_allowed(org_id: str) -> tuple[bool, dict]:
    """
    Check if the organization can perform an operation.

    Returns (allowed, info) where info contains:
    - current: current usage count
    - limit: monthly limit (-1 = unlimited)
    - remaining: operations remaining
    - tier: subscription tier
    """
    if not org_id:
        return True, {"current": 0, "limit": -1, "remaining": -1, "tier": "unknown"}

    limit = get_operation_limit(org_id)
    current = get_current_usage(org_id)

    if limit == -1:
        return True, {"current": current, "limit": -1, "remaining": -1, "tier": "unlimited"}

    remaining = max(0, limit - current)
    allowed = current < limit

    cached = _get_cached_limits(org_id) or {}
    tier = cached.get("tier", "unknown")

    return allowed, {
        "current": current,
        "limit": limit,
        "remaining": remaining,
        "tier": tier,
    }


def reset_counters():
    """Reset all counters (for testing)."""
    global _redis_init_attempted, _redis_client
    with _counters_lock:
        _counters.clear()
    _redis_init_attempted = False
    _redis_client = None


def clear_cache():
    """Clear the limits cache (for testing)."""
    with _limits_lock:
        _limits_cache.clear()
