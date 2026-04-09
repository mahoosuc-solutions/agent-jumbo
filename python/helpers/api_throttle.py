"""Reusable rate limiter decorator for external API calls."""

from __future__ import annotations

import asyncio
import logging
import time
from functools import wraps
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger("agent_mahoo")


class AsyncThrottle:
    """Simple sliding-window rate limiter for async functions."""

    def __init__(self, calls_per_minute: int = 30, retry_on_429: bool = True, max_retries: int = 5):
        self.interval = 60.0 / calls_per_minute
        self.retry_on_429 = retry_on_429
        self.max_retries = max_retries
        self._last_call: float = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self.interval:
                await asyncio.sleep(self.interval - elapsed)
            self._last_call = time.monotonic()


def throttled(calls_per_minute: int = 30, max_retries: int = 5):
    """Decorator: rate-limit and retry with exponential backoff on 429."""
    throttle = AsyncThrottle(calls_per_minute=calls_per_minute)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            await throttle.wait()
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "rate" in err_str.lower():
                        last_exc = e
                        backoff = min(2**attempt, 60)
                        logger.warning(
                            "Rate limited on %s (attempt %d/%d), backing off %.1fs",
                            func.__name__,
                            attempt + 1,
                            max_retries + 1,
                            backoff,
                        )
                        await asyncio.sleep(backoff)
                        continue
                    raise
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator
