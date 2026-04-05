"""E2E tests for upload and knowledge endpoint error paths.

Tests error handling only — no external services required.
All tests send malformed or incomplete requests and verify
that the server returns a structured error (not a raw traceback).
"""

import json
import urllib.error
import urllib.request

import pytest

from tests.e2e.helpers import cookie_header, get_csrf_token_and_cookies, with_retry

pytestmark = [pytest.mark.e2e]

# A minimal multipart body that contains a text field but NO file field.
_BOUNDARY = "----E2EBoundaryTest"
_MULTIPART_NO_FILE = (
    f'--{_BOUNDARY}\r\nContent-Disposition: form-data; name="other_field"\r\n\r\nsome_value\r\n--{_BOUNDARY}--\r\n'
).encode()
_MULTIPART_CONTENT_TYPE = f"multipart/form-data; boundary={_BOUNDARY}"


def _multipart_post(app_server, auth_cookies, path, body=None, content_type=None):
    """POST a multipart request with CSRF token. Returns (status, body_str)."""
    csrf, cookies = get_csrf_token_and_cookies(app_server, auth_cookies)
    data = body if body is not None else _MULTIPART_NO_FILE
    ct = content_type if content_type is not None else _MULTIPART_CONTENT_TYPE
    req = urllib.request.Request(
        f"{app_server}{path}",
        data=data,
        method="POST",
    )
    req.add_header("Cookie", cookie_header(cookies))
    req.add_header("Content-Type", ct)
    req.add_header("X-CSRF-Token", csrf)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status, resp.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def _json_post(app_server, auth_cookies, path, payload=None):
    """POST a JSON request with CSRF token. Returns (status, body_str)."""
    csrf, cookies = get_csrf_token_and_cookies(app_server, auth_cookies)
    data = json.dumps(payload if payload is not None else {}).encode()
    req = urllib.request.Request(
        f"{app_server}{path}",
        data=data,
        method="POST",
    )
    req.add_header("Cookie", cookie_header(cookies))
    req.add_header("Content-Type", "application/json")
    req.add_header("X-CSRF-Token", csrf)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status, resp.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@with_retry()
def test_upload_no_file_part(app_server, auth_cookies):
    """POST /upload without a 'file' field should return an error response."""
    status, body = _multipart_post(app_server, auth_cookies, "/upload")

    assert status in (400, 403, 500), f"Unexpected status {status}: {body}"
    assert "Traceback" not in body, "Server returned a raw Python traceback"
    # The response should indicate that no file was found
    body_lower = body.lower()
    assert "no file" in body_lower or "file part" in body_lower or "error" in body_lower or "missing" in body_lower, (
        f"Expected an error indication in body, got: {body[:300]}"
    )


@with_retry()
def test_upload_work_dir_no_files(app_server, auth_cookies):
    """POST /upload_work_dir_files without 'files[]' field should return an error."""
    status, body = _multipart_post(app_server, auth_cookies, "/upload_work_dir_files")

    assert status in (400, 403, 500), f"Unexpected status {status}: {body}"
    assert "Traceback" not in body, "Server returned a raw Python traceback"
    body_lower = body.lower()
    assert (
        "no files" in body_lower
        or "files" in body_lower
        or "error" in body_lower
        or "missing" in body_lower
        or "uploaded" in body_lower
    ), f"Expected an error indication in body, got: {body[:300]}"


@with_retry()
def test_import_knowledge_no_files(app_server, auth_cookies):
    """POST /import_knowledge without 'files[]' field should return an error."""
    status, body = _multipart_post(app_server, auth_cookies, "/import_knowledge")

    assert status in (400, 403, 500), f"Unexpected status {status}: {body}"
    assert "Traceback" not in body, "Server returned a raw Python traceback"
    body_lower = body.lower()
    assert "no files" in body_lower or "files part" in body_lower or "error" in body_lower or "missing" in body_lower, (
        f"Expected an error indication in body, got: {body[:300]}"
    )


@with_retry()
def test_knowledge_path_get_no_context(app_server, auth_cookies):
    """POST /knowledge_path_get with empty body should report a missing context id."""
    status, body = _json_post(app_server, auth_cookies, "/knowledge_path_get", {})

    assert status in (400, 403, 500), f"Unexpected status {status}: {body}"
    assert "Traceback" not in body, "Server returned a raw Python traceback"
    body_lower = body.lower()
    assert "context" in body_lower or "error" in body_lower or "missing" in body_lower or "required" in body_lower, (
        f"Expected an error indication in body, got: {body[:300]}"
    )


@with_retry()
def test_knowledge_reindex_no_context(app_server, auth_cookies):
    """POST /knowledge_reindex with empty body should report a missing context id."""
    status, body = _json_post(app_server, auth_cookies, "/knowledge_reindex", {})

    assert status in (400, 403, 500), f"Unexpected status {status}: {body}"
    assert "Traceback" not in body, "Server returned a raw Python traceback"
    body_lower = body.lower()
    assert "context" in body_lower or "error" in body_lower or "missing" in body_lower or "required" in body_lower, (
        f"Expected an error indication in body, got: {body[:300]}"
    )
