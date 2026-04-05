"""Shared E2E test helpers for Flask API endpoints.

Provides CSRF token management, cookie handling, and JSON API call wrappers
used across all E2E test modules.
"""

import functools
import json
import time
import urllib.error
import urllib.request


def with_retry(retries: int = 3, backoff: float = 5.0, retry_on: tuple = (429,)):
    """Decorator that retries a test function on HTTP rate-limit (429) errors.

    Usage::

        @with_retry(retries=3, backoff=5.0)
        def test_something(app_server, auth_cookies):
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except urllib.error.HTTPError as exc:
                    if exc.code in retry_on and attempt < retries - 1:
                        last_exc = exc
                        time.sleep(backoff * (attempt + 1))
                        continue
                    raise
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator


def cookie_header(cookies: dict) -> str:
    """Format a cookies dict into a Cookie header string."""
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


def parse_set_cookies(resp) -> dict:
    """Extract cookie name=value pairs from Set-Cookie response headers."""
    updates = {}
    for header in resp.headers.get_all("Set-Cookie") or []:
        parts = header.split(";")[0].strip()
        if "=" in parts:
            name, value = parts.split("=", 1)
            updates[name.strip()] = value.strip()
    return updates


def get_csrf_token_and_cookies(base_url: str, auth_cookies: dict, retries: int = 5) -> tuple[str, dict]:
    """Fetch a CSRF token and return (token, updated_cookies).

    The Flask session cookie is updated when /csrf_token generates a new token,
    so we must capture Set-Cookie and merge it into our cookies for the next request.
    """
    cookies = dict(auth_cookies)
    status = None
    for attempt in range(retries):
        req = urllib.request.Request(f"{base_url}/csrf_token", method="GET")
        req.add_header("Cookie", cookie_header(cookies))
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            cookies.update(parse_set_cookies(resp))
            data = json.loads(resp.read().decode())
            assert data.get("ok"), f"CSRF endpoint returned ok=false: {data}"
            return data["token"], cookies
        except urllib.error.HTTPError as e:
            status = e.code
            if e.code == 429 and attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise
    raise AssertionError(f"CSRF token fetch failed after {retries} retries (last status: {status})")


def api_post(app_server: str, auth_cookies: dict, endpoint: str, body: dict, timeout: int = 15) -> dict:
    """POST JSON to /<endpoint> with CSRF token and auth cookies.

    Captures the updated session cookie from /csrf_token so the CSRF check passes.
    Pass a larger ``timeout`` for endpoints that may block (e.g. /message when the
    agent is paused at a trust gate waiting for approval).
    """
    csrf, cookies = get_csrf_token_and_cookies(app_server, auth_cookies)
    payload = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{app_server}/{endpoint}",
        data=payload,
        method="POST",
    )
    req.add_header("Cookie", cookie_header(cookies))
    req.add_header("Content-Type", "application/json")
    req.add_header("X-CSRF-Token", csrf)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        exc._response_body = exc.read().decode(errors="replace")
        raise


def api_post_tolerant(
    app_server: str,
    auth_cookies: dict,
    endpoint: str,
    body: dict,
    retries: int = 3,
    backoff: float = 5.0,
) -> dict:
    """POST with retry on 429 rate-limit responses."""
    for attempt in range(retries):
        try:
            return api_post(app_server, auth_cookies, endpoint, body)
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
                continue
            raise
    raise AssertionError(f"api_post_tolerant failed after {retries} retries")


def api_get(app_server: str, auth_cookies: dict, endpoint: str) -> dict:
    """GET /<endpoint> with auth cookies. Returns parsed JSON."""
    req = urllib.request.Request(f"{app_server}/{endpoint}", method="GET")
    req.add_header("Cookie", cookie_header(auth_cookies))
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read().decode())


def api_get_tolerant(
    app_server: str,
    auth_cookies: dict,
    endpoint: str,
    retries: int = 3,
    backoff: float = 5.0,
) -> dict:
    """GET with retry on 429 rate-limit responses."""
    for attempt in range(retries):
        try:
            return api_get(app_server, auth_cookies, endpoint)
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
                continue
            raise
    raise AssertionError(f"api_get_tolerant failed after {retries} retries")
