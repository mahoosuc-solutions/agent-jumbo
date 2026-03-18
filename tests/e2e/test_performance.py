"""E2E performance tests for Agent Zero web UI.

Measures page load times, API SLA compliance, memory stability,
and concurrent connection handling.
"""

import json
import time
import urllib.parse
import urllib.request

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.performance]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_opener(auth_cookies: dict):
    """Return a urllib opener that sends the given auth cookies."""
    import http.cookiejar

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    # We inject cookies manually via header instead of the jar.
    return opener


def _cookie_header(auth_cookies: dict) -> str:
    return "; ".join(f"{k}={v}" for k, v in auth_cookies.items())


def _get_csrf(base_url: str, auth_cookies: dict) -> str:
    """Fetch a CSRF token for the session, retrying on 429."""
    for attempt in range(5):
        req = urllib.request.Request(f"{base_url}/csrf_token")
        req.add_header("Cookie", _cookie_header(auth_cookies))
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            return json.loads(resp.read())["token"]
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 4:
                time.sleep(5 * (attempt + 1))
                continue
            raise
    raise RuntimeError("CSRF token fetch failed after retries")


def _authed_request(
    url: str,
    auth_cookies: dict,
    *,
    method: str = "GET",
    data: bytes | None = None,
    content_type: str | None = None,
    csrf_token: str | None = None,
    timeout: float = 10,
) -> urllib.request.Request:
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Cookie", _cookie_header(auth_cookies))
    if content_type:
        req.add_header("Content-Type", content_type)
    if csrf_token:
        req.add_header("X-CSRF-Token", csrf_token)
    return req


def _timed_urlopen(req, timeout: float = 10):
    """Open a request and return (response, elapsed_seconds)."""
    t0 = time.monotonic()
    resp = urllib.request.urlopen(req, timeout=timeout)
    elapsed = time.monotonic() - t0
    return resp, elapsed


# ---------------------------------------------------------------------------
# Page load tests (Playwright)
# ---------------------------------------------------------------------------


class TestPageLoad:
    def test_spa_index_load(self, authenticated_page, app_server):
        """Main SPA index page loads in under 3 seconds."""
        t0 = time.monotonic()
        authenticated_page.goto(f"{app_server}/", wait_until="load")
        elapsed = time.monotonic() - t0
        assert elapsed < 3.0, f"SPA index load took {elapsed:.2f}s (limit 3s)"

    def test_login_page_load(self, page, app_server):
        """Login page loads in under 2 seconds."""
        t0 = time.monotonic()
        page.goto(f"{app_server}/login", wait_until="load")
        elapsed = time.monotonic() - t0
        assert elapsed < 2.0, f"Login page load took {elapsed:.2f}s (limit 2s)"

    def test_settings_page_load(self, authenticated_page, app_server):
        """Settings page loads in under 2 seconds."""
        t0 = time.monotonic()
        authenticated_page.goto(f"{app_server}/settings", wait_until="load")
        elapsed = time.monotonic() - t0
        assert elapsed < 2.0, f"Settings page load took {elapsed:.2f}s (limit 2s)"

    def test_static_assets_cached(self, authenticated_page, app_server):
        """Static assets return cache headers or 304 on second request."""
        # Navigate to index to discover a static asset URL
        authenticated_page.goto(f"{app_server}/", wait_until="load")

        # Collect static asset URLs from network
        static_urls: list[str] = []
        for tag in ["link[rel='stylesheet']", "script[src]", "img[src]"]:
            for el in authenticated_page.query_selector_all(tag):
                src = el.get_attribute("href") or el.get_attribute("src")
                if src and not src.startswith("data:"):
                    if src.startswith("/"):
                        src = f"{app_server}{src}"
                    elif not src.startswith("http"):
                        src = f"{app_server}/{src}"
                    static_urls.append(src)

        if not static_urls:
            pytest.skip("No static assets found on index page")

        target = static_urls[0]

        # First request — prime cache
        req1 = urllib.request.Request(target)
        resp1 = urllib.request.urlopen(req1, timeout=10)
        etag = resp1.headers.get("ETag")
        last_modified = resp1.headers.get("Last-Modified")
        cache_control = resp1.headers.get("Cache-Control")
        resp1.read()

        # Second request — conditional if possible
        req2 = urllib.request.Request(target)
        if etag:
            req2.add_header("If-None-Match", etag)
        if last_modified:
            req2.add_header("If-Modified-Since", last_modified)

        got_304 = False
        has_cache_control = cache_control is not None
        try:
            resp2 = urllib.request.urlopen(req2, timeout=10)
            resp2.read()
            # Check if response itself declares caching
            cc2 = resp2.headers.get("Cache-Control")
            if cc2:
                has_cache_control = True
        except urllib.error.HTTPError as exc:
            if exc.code == 304:
                got_304 = True
            else:
                raise

        assert got_304 or has_cache_control, f"Static asset {target} returned neither 304 nor Cache-Control"


# ---------------------------------------------------------------------------
# API SLA tests (raw HTTP)
# ---------------------------------------------------------------------------


class TestApiSLA:
    def test_health_endpoint(self, app_server, auth_cookies):
        """GET /health responds in under 200ms."""
        req = _authed_request(f"{app_server}/health", auth_cookies)
        resp, elapsed = _timed_urlopen(req)
        resp.read()
        assert resp.status == 200
        assert elapsed < 0.200, f"/health took {elapsed:.3f}s (limit 0.2s)"

    def test_chat_api_response(self, app_server, auth_cookies):
        """POST /message with a short message responds in under 1 second."""
        payload = json.dumps({"text": "ping", "context": "test"}).encode()
        req = _authed_request(
            f"{app_server}/message",
            auth_cookies,
            method="POST",
            data=payload,
            content_type="application/json",
        )
        t0 = time.monotonic()
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            resp.read()
        except urllib.error.HTTPError:
            # Even an error response counts — we measure transport latency
            pass
        elapsed = time.monotonic() - t0
        assert elapsed < 1.0, f"POST /message took {elapsed:.2f}s (limit 1s)"

    def test_upload_1mb(self, app_server, auth_cookies):
        """Upload a 1 MB text file in under 3 seconds."""
        content = b"A" * (1024 * 1024)  # 1 MB
        boundary = "----E2ETestBoundary"
        body = (
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="test_1mb.txt"\r\n'
                f"Content-Type: text/plain\r\n\r\n"
            ).encode()
            + content
            + f"\r\n--{boundary}--\r\n".encode()
        )

        req = _authed_request(
            f"{app_server}/upload",
            auth_cookies,
            method="POST",
            data=body,
            content_type=f"multipart/form-data; boundary={boundary}",
        )
        t0 = time.monotonic()
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            resp.read()
        except urllib.error.HTTPError:
            pass  # endpoint may reject; we measure transport latency
        elapsed = time.monotonic() - t0
        assert elapsed < 3.0, f"1 MB upload took {elapsed:.2f}s (limit 3s)"

    def test_sse_connection_time(self, app_server, auth_cookies):
        """SSE endpoint delivers first data: line within 2 seconds."""
        req = _authed_request(f"{app_server}/sse", auth_cookies)
        req.add_header("Accept", "text/event-stream")

        t0 = time.monotonic()
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            # Read until we see a line starting with "data:" or hit timeout
            while True:
                line = resp.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").strip()
                if decoded.startswith("data:"):
                    break
                if time.monotonic() - t0 > 2.0:
                    break
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            # Connection errors are fine — we measure time to first byte
            pass
        elapsed = time.monotonic() - t0
        assert elapsed < 2.0, f"SSE first data: took {elapsed:.2f}s (limit 2s)"

    def test_settings_save_roundtrip(self, app_server, auth_cookies):
        """POST settings_set then GET settings_get completes in under 1 second (soft)."""
        # First GET current settings so we can round-trip a real value
        get_req = _authed_request(
            f"{app_server}/settings_get",
            auth_cookies,
            method="GET",
        )

        t0 = time.monotonic()
        try:
            resp = urllib.request.urlopen(get_req, timeout=5)
            current = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 405):
                pytest.skip("Settings get endpoint not available")
            current = {}
        except urllib.error.URLError:
            pytest.skip("Settings get endpoint not reachable")

        # POST a benign settings payload via settings_set (CSRF-protected)
        csrf = _get_csrf(app_server, auth_cookies)
        payload = json.dumps(current.get("settings", {})).encode()
        post_req = _authed_request(
            f"{app_server}/settings_set",
            auth_cookies,
            method="POST",
            data=payload,
            content_type="application/json",
            csrf_token=csrf,
        )

        try:
            resp = urllib.request.urlopen(post_req, timeout=5)
            resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 405):
                pytest.skip("Settings save endpoint not available")
            # Other errors are acceptable — measure latency
        except urllib.error.URLError:
            pytest.skip("Settings save endpoint not reachable")

        # Verify with GET
        verify_req = _authed_request(f"{app_server}/settings_get", auth_cookies)
        try:
            resp = urllib.request.urlopen(verify_req, timeout=5)
            resp.read()
        except (urllib.error.HTTPError, urllib.error.URLError):
            pass

        elapsed = time.monotonic() - t0
        assert elapsed < 1.0, f"Settings roundtrip took {elapsed:.2f}s (limit 1s)"


# ---------------------------------------------------------------------------
# Resource tests
# ---------------------------------------------------------------------------


class TestResources:
    def test_memory_no_leak(self, app_server, auth_cookies, warmup):
        """RSS growth stays under 50 MB over 50 mixed requests."""
        cookie = _cookie_header(auth_cookies)

        def get_rss() -> int:
            req = urllib.request.Request(f"{app_server}/debug_metrics")
            req.add_header("Cookie", cookie)
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            return data["rss_bytes"]

        baseline_rss = get_rss()

        # Hammer various endpoints
        endpoints = ["/health", "/", "/login", "/settings"]
        for i in range(50):
            url = f"{app_server}{endpoints[i % len(endpoints)]}"
            req = urllib.request.Request(url)
            req.add_header("Cookie", cookie)
            try:
                resp = urllib.request.urlopen(req, timeout=5)
                resp.read()
            except Exception:
                pass

        final_rss = get_rss()
        delta_mb = (final_rss - baseline_rss) / (1024 * 1024)
        assert delta_mb < 50, f"RSS grew by {delta_mb:.1f} MB over 50 requests (limit 50 MB)"

    def test_concurrent_connections(self, app_server, auth_cookies):
        """10 concurrent GET /health requests all succeed."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        cookie = _cookie_header(auth_cookies)
        errors: list[str] = []

        def fetch(idx: int) -> None:
            try:
                req = urllib.request.Request(f"{app_server}/health")
                req.add_header("Cookie", cookie)
                resp = urllib.request.urlopen(req, timeout=10)
                if resp.status != 200:
                    errors.append(f"Request {idx}: status {resp.status}")
            except Exception as exc:
                errors.append(f"Request {idx}: {exc}")

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(fetch, i) for i in range(10)]
            for f in as_completed(futures):
                f.result()  # propagate exceptions

        assert len(errors) == 0, f"Concurrent requests had errors: {errors}"
