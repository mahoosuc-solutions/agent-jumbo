"""Tests for usage enforcement — Redis-backed counters + tier limits."""

import time
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset module state between tests."""
    import python.helpers.usage_enforcement as u

    u.reset_counters()
    u.clear_cache()
    yield
    u.reset_counters()
    u.clear_cache()


class TestInMemoryCounters:
    """Tests for in-memory fallback (no Redis)."""

    def test_increment_and_read(self):
        from python.helpers.usage_enforcement import get_current_usage, increment_usage

        assert get_current_usage("org-1") == 0
        assert increment_usage("org-1") == 1
        assert increment_usage("org-1") == 2
        assert get_current_usage("org-1") == 2

    def test_separate_orgs(self):
        from python.helpers.usage_enforcement import get_current_usage, increment_usage

        increment_usage("org-a", 5)
        increment_usage("org-b", 10)

        assert get_current_usage("org-a") == 5
        assert get_current_usage("org-b") == 10

    def test_reset_clears_counters(self):
        from python.helpers.usage_enforcement import get_current_usage, increment_usage, reset_counters

        increment_usage("org-1", 100)
        assert get_current_usage("org-1") == 100

        reset_counters()
        assert get_current_usage("org-1") == 0


class TestRedisCounters:
    """Tests for Redis-backed counters."""

    def test_increment_uses_redis_when_available(self, monkeypatch):
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.incrby.return_value = 5
        mock_redis.get.return_value = "5"

        import python.helpers.usage_enforcement as u

        u._redis_client = mock_redis
        u._redis_init_attempted = True

        assert u.increment_usage("org-r1") == 5
        assert mock_redis.incrby.called

    def test_get_usage_reads_from_redis(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "42"

        import python.helpers.usage_enforcement as u

        u._redis_client = mock_redis
        u._redis_init_attempted = True

        assert u.get_current_usage("org-r2") == 42

    def test_falls_back_to_memory_on_redis_error(self):
        mock_redis = MagicMock()
        mock_redis.incrby.side_effect = ConnectionError("redis down")
        mock_redis.get.side_effect = ConnectionError("redis down")

        import python.helpers.usage_enforcement as u

        u._redis_client = mock_redis
        u._redis_init_attempted = True

        # Should fall back to in-memory
        assert u.increment_usage("org-r3") == 1
        assert u.get_current_usage("org-r3") == 1


class TestUsageAllowed:
    """Tests for check_usage_allowed()."""

    def test_allows_when_under_limit(self):
        from python.helpers.usage_enforcement import check_usage_allowed, increment_usage

        # In standalone mode, default trial tier is "professional" (5000 ops)
        increment_usage("org-check", 50)
        allowed, info = check_usage_allowed("org-check")

        assert allowed is True
        assert info["current"] == 50
        assert info["remaining"] > 0

    def test_denies_when_at_limit(self):
        import python.helpers.usage_enforcement as u
        from python.helpers.usage_enforcement import check_usage_allowed, increment_usage

        # Seed free tier in cache to get a low limit (100)
        u._limits_cache["org-full"] = {"tier": "free", "_fetched_at": time.time()}
        increment_usage("org-full", 100)
        allowed, info = check_usage_allowed("org-full")

        assert allowed is False
        assert info["current"] == 100
        assert info["remaining"] == 0

    def test_unlimited_for_empty_org(self):
        from python.helpers.usage_enforcement import check_usage_allowed

        allowed, info = check_usage_allowed("")
        assert allowed is True
        assert info["limit"] == -1

    def test_respects_tier_defaults(self):
        import python.helpers.usage_enforcement as u

        # Seed starter tier in cache
        u._limits_cache["org-starter"] = {"tier": "starter", "_fetched_at": time.time()}

        u.increment_usage("org-starter", 499)
        allowed, _ = u.check_usage_allowed("org-starter")
        assert allowed is True

        u.increment_usage("org-starter", 1)  # Now at 500 = starter limit
        allowed, info = u.check_usage_allowed("org-starter")
        assert allowed is False
        assert info["limit"] == 500


class TestMonthlyKeyRollover:
    """Tests for monthly key generation."""

    def test_key_includes_month(self):
        from python.helpers.usage_enforcement import _current_month_key

        key = _current_month_key("org-1")
        month = time.strftime("%Y-%m")
        assert key == f"org-1:{month}"
