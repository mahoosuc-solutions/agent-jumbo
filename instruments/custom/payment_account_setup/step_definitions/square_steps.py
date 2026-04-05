"""Square account setup step definitions."""

from __future__ import annotations


def get_square_steps(session_id: str, email: str, webhook_endpoint_url: str) -> list[dict]:
    """Return the ordered list of Square account setup steps."""

    def step(index: int, **kwargs) -> dict:
        return {"step_id": f"{session_id}_s{index:02d}", "session_id": session_id, "step_index": index, **kwargs}

    return [
        step(
            0,
            title="Navigate to Square registration",
            description="Open the Square business sign-up page.",
            automation_type="automated",
            human_instructions="",
            action={"tool": "browser_navigate", "args": {"url": "https://squareup.com/signup/new-account"}},
            completion_check="input[name='email_address']",
            extract_fields=[],
        ),
        step(
            1,
            title="Screenshot registration page",
            description="Capture the registration form for operator review.",
            automation_type="automated",
            human_instructions="",
            action={"tool": "browser_take_screenshot", "args": {}},
            completion_check="",
            extract_fields=[],
        ),
        step(
            2,
            title="Fill Square registration form",
            description=f"Enter the business email ({email}) and password.",
            automation_type="automated",
            human_instructions="",
            action={
                "tool": "browser_fill_form",
                "args": {
                    "fields": [
                        {"selector": "input[name='email_address']", "value": email},
                        {"selector": "input[name='password']", "value": "__OPERATOR_SETS_PASSWORD__"},
                    ]
                },
            },
            completion_check="button[type='submit']",
            extract_fields=[],
        ),
        step(
            3,
            title="Submit Square registration",
            description="Click Create Account.",
            automation_type="automated",
            human_instructions="",
            action={"tool": "browser_click", "args": {"selector": "button[type='submit']"}},
            completion_check="",
            extract_fields=[],
        ),
        step(
            4,
            title="Email verification — human required",
            description="Square sends an email verification link.",
            automation_type="human_required",
            human_instructions=(
                "Check your inbox and click the verification link Square sent. "
                "Press Continue when your Square account is verified and the dashboard is open."
            ),
            action={},
            completion_check="",
            extract_fields=[],
        ),
        step(
            5,
            title="Identity verification — human required",
            description="Square may require identity or business verification documents.",
            automation_type="human_required",
            human_instructions=(
                "Complete any identity or business verification steps Square is showing. "
                "You may need to provide your business name, address, or EIN. "
                "Press Continue when done."
            ),
            action={},
            completion_check="",
            extract_fields=[],
        ),
        step(
            6,
            title="Navigate to Square Developer Portal",
            description="Open the Square Developer Portal to create an API application.",
            automation_type="automated",
            human_instructions="",
            action={
                "tool": "browser_navigate",
                "args": {"url": "https://developer.squareup.com/apps"},
            },
            completion_check="",
            extract_fields=[],
        ),
        step(
            7,
            title="Create new Square application",
            description="Click New Application and name it 'Agent Jumbo'.",
            automation_type="automated",
            human_instructions=(
                "If the agent cannot find the New Application button, "
                "click it manually and name the app 'Agent Jumbo'. Press Continue when created."
            ),
            action={
                "tool": "browser_click",
                "args": {"selector": "[data-testid='new-application-button'], button:contains('New Application')"},
            },
            completion_check="",
            extract_fields=[],
        ),
        step(
            8,
            title="Extract Square Application ID and Secret",
            description="Navigate to the app credentials page and extract the sandbox Application ID and secret.",
            automation_type="automated",
            human_instructions=(
                "If automatic extraction fails, note the Application ID (starts with 'sandbox-sq0idb-') "
                "and Application Secret. Press Continue when ready to provide them manually."
            ),
            action={
                "tool": "browser_evaluate",
                "args": {
                    "script": (
                        "(() => {"
                        "  const appId = document.querySelector('[data-field=\"application_id\"]')"
                        "    || document.querySelector('.application-id');"
                        "  const secret = document.querySelector('[data-field=\"application_secret\"]')"
                        "    || document.querySelector('.application-secret');"
                        "  return {"
                        "    application_id: appId ? (appId.value || appId.textContent || '').trim() : null,"
                        "    application_secret: secret ? (secret.value || secret.textContent || '').trim() : null,"
                        "  };"
                        "})()"
                    )
                },
            },
            completion_check="",
            extract_fields=["square_application_id", "square_application_secret"],
        ),
        step(
            9,
            title="Navigate to webhook subscriptions",
            description="Open the webhook subscriptions section for the app.",
            automation_type="automated",
            human_instructions="",
            action={
                "tool": "browser_navigate",
                "args": {"url": "https://developer.squareup.com/apps"},
            },
            completion_check="",
            extract_fields=[],
        ),
        step(
            10,
            title="Register Square webhook endpoint",
            description=f"Add webhook subscription pointing to {webhook_endpoint_url}",
            automation_type="human_required",
            human_instructions=(
                f"In the Square Developer Portal → your app → Webhooks, "
                f"click 'Add Subscription', enter the notification URL: {webhook_endpoint_url}, "
                f"select the events: payment.updated, invoice.payment_failed, subscription.updated. "
                f"After saving, copy the Signature Key. Press Continue when done."
            ),
            action={},
            completion_check="",
            extract_fields=[],
        ),
        step(
            11,
            title="Enter Square webhook signature key",
            description="Prompt operator to paste the webhook signature key.",
            automation_type="human_required",
            human_instructions=(
                "Paste the Webhook Signature Key from the Square developer portal "
                "into the setup session using the store_credentials action. "
                "The key will be stored as SQUARE_WEBHOOK_SIGNATURE_KEY."
            ),
            action={},
            completion_check="",
            extract_fields=["square_webhook_signature_key"],
        ),
        step(
            12,
            title="Store Square credentials",
            description="Save all extracted credentials to the credential store.",
            automation_type="automated",
            human_instructions="",
            action={"tool": "internal_store_credentials", "args": {"provider": "square"}},
            completion_check="",
            extract_fields=[],
        ),
    ]
