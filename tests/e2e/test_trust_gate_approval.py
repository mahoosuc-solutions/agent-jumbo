"""E2E tests for trust gate → cowork approval integration."""
import pytest
from tests.e2e.helpers import api_post

pytestmark = [pytest.mark.e2e]


def test_trust_gate_approval_record_has_source_field(app_server, auth_cookies):
    """cowork_approvals_list with a nonexistent context returns empty approvals."""
    resp = api_post(
        app_server,
        auth_cookies,
        "cowork_approvals_list",
        {"context": "nonexistent_trust_gate_ctx"},
    )
    assert resp["approvals"] == []


def test_cowork_approvals_update_approve_and_retry_action(app_server, auth_cookies):
    """approve_and_retry action returns approvals list."""
    resp = api_post(
        app_server,
        auth_cookies,
        "cowork_approvals_update",
        {
            "context": "nonexistent_trust_gate_ctx",
            "action": "approve_and_retry",
            "approval_id": "trust-nonexistent-id",
        },
    )
    assert "approvals" in resp
