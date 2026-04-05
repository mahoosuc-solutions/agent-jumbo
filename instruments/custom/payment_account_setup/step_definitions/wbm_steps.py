"""Step definitions for the embedded WBM onboarding workflow."""

from __future__ import annotations


def get_wbm_steps(session_id: str) -> list[dict]:
    phases = [
        (
            "verify_bridge",
            "Verify MCP Bridge",
            "Confirm the WBM staging and production bridge health before changing tenant state.",
        ),
        (
            "bootstrap_tenant",
            "Bootstrap Tenant",
            "Run the onboarding summary and tenant bootstrap flow for the property workspace.",
        ),
        (
            "property_configuration",
            "Property Configuration",
            "Set property identity, contact, timezone, and guest-facing baseline configuration.",
        ),
        (
            "room_inventory",
            "Room Inventory",
            "Create and validate room inventory before bookings or operational automations rely on it.",
        ),
        (
            "staff_access",
            "Staff Access",
            "Set up staff-facing access, roles, and operator permissions.",
        ),
        (
            "email_setup",
            "Email",
            "Configure guest communication email flows and validate sender settings.",
        ),
        (
            "voice_ai",
            "Voice AI",
            "Configure the voice assistant path and confirm the scripted property experience.",
        ),
        (
            "sms_setup",
            "SMS",
            "Enable SMS delivery and confirm messaging configuration.",
        ),
        (
            "door_codes",
            "Door Codes",
            "Connect code issuance behavior with check-in and room access settings.",
        ),
        (
            "payments",
            "Payments",
            "Confirm payment settings and the billing-related WBM integration points for the property.",
        ),
        (
            "occupancy_rates",
            "Occupancy & Rates",
            "Configure occupancy baselines and revenue-facing rate inputs.",
        ),
        (
            "competitor_intel",
            "Competitor Intel",
            "Establish competitive monitoring inputs that support pricing and market awareness.",
        ),
        (
            "dynamic_pricing",
            "Dynamic Pricing",
            "Configure pricing automation guardrails and validate activation prerequisites.",
        ),
        (
            "seo_web_presence",
            "SEO & Web Presence",
            "Set property web presence, listing, and discoverability details used by public surfaces.",
        ),
        (
            "final_validation",
            "Final Validation",
            "Run the final validation suite and capture evidence that the property onboarding is operational.",
        ),
    ]

    steps: list[dict] = []
    for index, (slug, title, description) in enumerate(phases):
        steps.append(
            {
                "step_id": f"{session_id}_{slug}",
                "step_index": index,
                "title": title,
                "description": description,
                "automation_type": "human_required",
                "human_instructions": (
                    "Use the embedded WBM onboarding workflow to complete this phase, then confirm it here so the "
                    "session can capture evidence and create a safe recovery checkpoint."
                ),
                "action": {"tool": "wbm_embedded_workflow", "args": {"phase": slug}},
                "completion_check": "",
                "extract_fields": [],
            }
        )
    return steps
