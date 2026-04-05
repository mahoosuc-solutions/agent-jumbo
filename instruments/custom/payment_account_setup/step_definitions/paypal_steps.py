"""PayPal business account setup step definitions."""

from __future__ import annotations


def get_paypal_steps(session_id: str, email: str, webhook_endpoint_url: str) -> list[dict]:
    """Return the ordered list of PayPal account setup steps."""

    def step(index: int, **kwargs) -> dict:
        return {"step_id": f"{session_id}_s{index:02d}", "session_id": session_id, "step_index": index, **kwargs}

    return [
        step(
            0,
            title="Navigate to PayPal business sign-up",
            description="Open the PayPal business account registration page.",
            automation_type="automated",
            human_instructions="",
            action={
                "tool": "browser_navigate",
                "args": {"url": "https://www.paypal.com/us/webapps/mpp/account-selection"},
            },
            completion_check="",
            extract_fields=[],
        ),
        step(
            1,
            title="Screenshot registration page",
            description="Capture the sign-up page for operator review.",
            automation_type="automated",
            human_instructions="",
            action={"tool": "browser_take_screenshot", "args": {}},
            completion_check="",
            extract_fields=[],
        ),
        step(
            2,
            title="Select Business account type",
            description="Click 'Business' account type to start business registration.",
            automation_type="automated",
            human_instructions="",
            action={
                "tool": "browser_click",
                "args": {"selector": "a[href*='bizsignup'], button:contains('Business')"},
            },
            completion_check="",
            extract_fields=[],
        ),
        step(
            3,
            title="Fill PayPal registration form",
            description=f"Enter the business email ({email}).",
            automation_type="automated",
            human_instructions="",
            action={
                "tool": "browser_fill_form",
                "args": {
                    "fields": [
                        {"selector": "input[name='email'], input[id='email']", "value": email},
                    ]
                },
            },
            completion_check="button[type='submit'], input[type='submit']",
            extract_fields=[],
        ),
        step(
            4,
            title="Email verification — human required",
            description="PayPal sends a verification email.",
            automation_type="human_required",
            human_instructions=(
                "Check your inbox and click the confirmation link PayPal sent. "
                "Press Continue when your PayPal account email is confirmed."
            ),
            action={},
            completion_check="",
            extract_fields=[],
        ),
        step(
            5,
            title="Phone verification — human required",
            description="PayPal may require SMS verification.",
            automation_type="human_required",
            human_instructions=(
                "If PayPal is asking for phone verification, complete it now. Enter the SMS code and press Continue."
            ),
            action={},
            completion_check="",
            extract_fields=[],
        ),
        step(
            6,
            title="Business information — human required",
            description="PayPal requires business details (name, address, EIN, etc.).",
            automation_type="human_required",
            human_instructions=(
                "Complete the business information form PayPal is showing. "
                "You will need: legal business name, business address, "
                "business type, and optionally your EIN/Tax ID. "
                "Press Continue when your PayPal business profile is set up."
            ),
            action={},
            completion_check="",
            extract_fields=[],
        ),
        step(
            7,
            title="Navigate to PayPal Developer Dashboard",
            description="Open the PayPal developer sandbox applications page.",
            automation_type="automated",
            human_instructions="",
            action={
                "tool": "browser_navigate",
                "args": {"url": "https://developer.paypal.com/dashboard/applications/sandbox"},
            },
            completion_check="",
            extract_fields=[],
        ),
        step(
            8,
            title="Screenshot developer dashboard",
            description="Capture the developer dashboard for the operator.",
            automation_type="automated",
            human_instructions="",
            action={"tool": "browser_take_screenshot", "args": {}},
            completion_check="",
            extract_fields=[],
        ),
        step(
            9,
            title="Create PayPal REST API app — human required",
            description="Create a sandbox REST API application to get Client ID and Secret.",
            automation_type="human_required",
            human_instructions=(
                "In the PayPal Developer Dashboard → My Apps & Credentials → Sandbox, "
                "click 'Create App', name it 'Agent Jumbo', then copy the "
                "Client ID and Client Secret shown. "
                "Press Continue when you have them."
            ),
            action={},
            completion_check="",
            extract_fields=["paypal_client_id", "paypal_client_secret"],
        ),
        step(
            10,
            title="Extract PayPal credentials from page (attempt)",
            description="Try to extract Client ID and Secret from the page automatically.",
            automation_type="automated",
            human_instructions=(
                "If automatic extraction fails, enter the Client ID and Secret manually "
                "using the store_credentials action. Press Continue."
            ),
            action={
                "tool": "browser_evaluate",
                "args": {
                    "script": (
                        "(() => {"
                        "  const clientId = document.querySelector('[data-field=\"client_id\"]')"
                        "    || document.querySelector('.client-id');"
                        "  return {"
                        "    paypal_client_id: clientId ? (clientId.value || clientId.textContent || '').trim() : null,"
                        "  };"
                        "})()"
                    )
                },
            },
            completion_check="",
            extract_fields=["paypal_client_id"],
        ),
        step(
            11,
            title="Register PayPal webhook endpoint — human required",
            description="Register the webhook endpoint in the PayPal developer portal.",
            automation_type="human_required",
            human_instructions=(
                f"In the PayPal Developer Dashboard → Webhooks, "
                f"click 'Add Webhook', enter the URL: {webhook_endpoint_url}, "
                f"and select these event types: "
                f"BILLING.SUBSCRIPTION.ACTIVATED, BILLING.SUBSCRIPTION.CANCELLED, "
                f"PAYMENT.SALE.COMPLETED, PAYMENT.SALE.DENIED, INVOICING.INVOICE.PAID. "
                f"After saving, copy the Webhook ID. Press Continue when done."
            ),
            action={},
            completion_check="",
            extract_fields=["paypal_webhook_id"],
        ),
        step(
            12,
            title="Store PayPal credentials",
            description="Save all extracted credentials to the credential store.",
            automation_type="automated",
            human_instructions="",
            action={"tool": "internal_store_credentials", "args": {"provider": "paypal"}},
            completion_check="",
            extract_fields=[],
        ),
    ]
