"""Stripe account setup step definitions.

Steps are returned as a list of dicts suitable for storage in SetupDatabase.
Each dict maps directly to the ``setup_steps`` schema fields.

Automation types:
- ``automated``      — the agent executes this step using MCP browser tools
- ``human_required`` — the agent pauses and displays instructions to the operator
- ``verification``   — automated check that a prior step succeeded
"""

from __future__ import annotations


def get_stripe_steps(session_id: str, email: str, webhook_endpoint_url: str) -> list[dict]:
    """Return the ordered list of Stripe account setup steps.

    Args:
        session_id: The parent session identifier (used to namespace step IDs).
        email: The business email address to pre-fill on the registration form.
        webhook_endpoint_url: The public URL Agent Mahoo will receive webhook events on.
    """

    def step(index: int, **kwargs) -> dict:
        return {"step_id": f"{session_id}_s{index:02d}", "session_id": session_id, "step_index": index, **kwargs}

    return [
        step(
            0,
            title="Navigate to Stripe registration",
            description="Open the Stripe sign-up page in the browser.",
            automation_type="automated",
            human_instructions="",
            action={"tool": "browser_navigate", "args": {"url": "https://dashboard.stripe.com/register"}},
            completion_check="input[name='email']",
            extract_fields=[],
        ),
        step(
            1,
            title="Screenshot registration page",
            description="Capture the current state of the registration form for the operator.",
            automation_type="automated",
            human_instructions="",
            action={"tool": "browser_take_screenshot", "args": {}},
            completion_check="",
            extract_fields=[],
        ),
        step(
            2,
            title="Fill registration form",
            description=f"Enter the business email ({email}) and a strong password.",
            automation_type="automated",
            human_instructions="",
            action={
                "tool": "browser_fill_form",
                "args": {
                    "fields": [
                        {"selector": "input[name='email']", "value": email},
                        {"selector": "input[name='password']", "value": "__OPERATOR_SETS_PASSWORD__"},
                    ]
                },
            },
            completion_check="button[type='submit']",
            extract_fields=[],
        ),
        step(
            3,
            title="Submit registration form",
            description="Click the Create Account button.",
            automation_type="automated",
            human_instructions="",
            action={"tool": "browser_click", "args": {"selector": "button[type='submit']"}},
            completion_check="",
            extract_fields=[],
        ),
        step(
            4,
            title="Email verification — human required",
            description="Stripe sends a verification email. The operator must click the link.",
            automation_type="human_required",
            human_instructions=(
                "Check your inbox at the email address you used to register. "
                "Click the verification link Stripe sent you. "
                "Return here and press Continue when the Stripe dashboard has loaded."
            ),
            action={},
            completion_check="",
            extract_fields=[],
        ),
        step(
            5,
            title="CAPTCHA / identity check — human required",
            description="Stripe may present a CAPTCHA or identity challenge.",
            automation_type="human_required",
            human_instructions=(
                "If a CAPTCHA or identity challenge is shown in the browser, complete it now. "
                "Press Continue when you are past it."
            ),
            action={},
            completion_check="",
            extract_fields=[],
        ),
        step(
            6,
            title="Two-factor authentication setup — human required",
            description="Stripe may prompt the operator to set up 2FA.",
            automation_type="human_required",
            human_instructions=(
                "If Stripe is asking you to set up two-factor authentication, do so now. "
                "Use an authenticator app or SMS. Press Continue when 2FA is configured."
            ),
            action={},
            completion_check="",
            extract_fields=[],
        ),
        step(
            7,
            title="Navigate to API Keys page",
            description="Open the Stripe test-mode API keys page.",
            automation_type="automated",
            human_instructions="",
            action={
                "tool": "browser_navigate",
                "args": {"url": "https://dashboard.stripe.com/test/apikeys"},
            },
            completion_check="[data-testid='api-keys-list']",
            extract_fields=[],
        ),
        step(
            8,
            title="Screenshot API keys page",
            description="Capture the API keys page so the operator can verify.",
            automation_type="automated",
            human_instructions="",
            action={"tool": "browser_take_screenshot", "args": {}},
            completion_check="",
            extract_fields=[],
        ),
        step(
            9,
            title="Reveal and extract test secret key",
            description="Click Reveal test key, then extract the sk_test_... value.",
            automation_type="automated",
            human_instructions=(
                "If Stripe asks for your password or 2FA code to reveal the key, enter it now. Then press Continue."
            ),
            action={
                "tool": "browser_evaluate",
                "args": {
                    "script": (
                        "(() => {"
                        "  const btn = document.querySelector('[data-testid=\"reveal-key-button\"]');"
                        "  if (btn) btn.click();"
                        "  setTimeout(() => {}, 1000);"
                        "  const el = document.querySelector('[data-testid=\"api-key-value\"]')"
                        "    || document.querySelector('.ReadOnlyApiKey-value')"
                        "    || document.querySelector('input[name=\"key\"]');"
                        "  return el ? (el.value || el.textContent || '').trim() : null;"
                        "})()"
                    )
                },
            },
            completion_check="",
            extract_fields=["stripe_secret_key"],
        ),
        step(
            10,
            title="Navigate to webhooks — create endpoint",
            description="Open the Stripe webhook creation page.",
            automation_type="automated",
            human_instructions="",
            action={
                "tool": "browser_navigate",
                "args": {"url": "https://dashboard.stripe.com/test/webhooks/create"},
            },
            completion_check="input[name='url']",
            extract_fields=[],
        ),
        step(
            11,
            title="Register webhook endpoint URL",
            description=f"Enter the webhook endpoint: {webhook_endpoint_url}",
            automation_type="automated",
            human_instructions="",
            action={
                "tool": "browser_fill_form",
                "args": {
                    "fields": [
                        {"selector": "input[name='url']", "value": webhook_endpoint_url},
                    ]
                },
            },
            completion_check="button[type='submit']",
            extract_fields=[],
        ),
        step(
            12,
            title="Extract webhook signing secret",
            description="After saving the webhook, extract the whsec_... signing secret.",
            automation_type="automated",
            human_instructions=(
                "After clicking Add endpoint, the signing secret will be displayed once. "
                "The agent will attempt to capture it automatically. "
                "If the agent cannot extract it, copy it manually and enter it when prompted."
            ),
            action={
                "tool": "browser_evaluate",
                "args": {
                    "script": (
                        "(() => {"
                        "  const els = [...document.querySelectorAll('*')]"
                        "    .filter(el => (el.textContent || '').includes('whsec_'));"
                        "  const el = els[els.length - 1];"
                        "  if (!el) return null;"
                        "  const text = el.textContent || '';"
                        "  const m = text.match(/whsec_[A-Za-z0-9]+/);"
                        "  return m ? m[0] : null;"
                        "})()"
                    )
                },
            },
            completion_check="",
            extract_fields=["stripe_webhook_secret"],
        ),
        step(
            13,
            title="Store credentials",
            description="Save the extracted API key and webhook secret to the credential store.",
            automation_type="automated",
            human_instructions="",
            action={"tool": "internal_store_credentials", "args": {"provider": "stripe"}},
            completion_check="",
            extract_fields=[],
        ),
        step(
            14,
            title="Verify catalog sync (dry-run)",
            description="Run stripe_catalog_sync.py --dry-run to validate the setup.",
            automation_type="automated",
            human_instructions="",
            action={
                "tool": "internal_shell",
                "args": {"command": "python3 scripts/stripe_catalog_sync.py --dry-run --catalog both"},
            },
            completion_check="",
            extract_fields=["dry_run_output"],
        ),
    ]
