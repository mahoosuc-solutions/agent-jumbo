"""Payment account setup and billing copilot manager."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from instruments.custom.payment_account_setup.credential_store import CredentialStore
from instruments.custom.payment_account_setup.setup_db import SetupDatabase
from python.helpers.stripe_catalog import load_commercial_catalog

logger = logging.getLogger(__name__)

_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "payment_account_setup.db")
_DEFAULT_TENANT_ID = "default"


class PaymentAccountSetupManager:
    """Manages guided payment-provider setup and tenant billing readiness."""

    def __init__(self, db_path: str | None = None):
        resolved_db_path = db_path or os.environ.get("PAYMENT_ACCOUNT_SETUP_DB_PATH") or _DB_PATH
        self.db = SetupDatabase(resolved_db_path)
        self.credential_store = CredentialStore()

    # -- session lifecycle ---------------------------------------------------

    def start_setup(
        self,
        provider: str,
        business_name: str,
        email: str,
        country: str = "us",
        webhook_endpoint_url: str = "",
        tenant_id: str = _DEFAULT_TENANT_ID,
    ) -> dict[str, Any]:
        provider = provider.lower().strip()
        tenant_id = self._normalize_tenant_id(tenant_id)
        if provider not in ("stripe", "square", "paypal"):
            raise ValueError(f"Unsupported provider '{provider}'. Choose: stripe, square, paypal")

        session_id = f"{provider}_{uuid.uuid4().hex[:8]}"
        if not webhook_endpoint_url:
            webhook_endpoint_url = self._default_webhook_url(provider)

        self.db.create_session(
            session_id=session_id,
            tenant_id=tenant_id,
            provider=provider,
            business_name=business_name,
            email=email,
            country=country,
            phase="guided_setup",
        )

        steps = self._load_steps(provider, session_id, email, webhook_endpoint_url)
        for s in steps:
            self.db.insert_step(
                step_id=s["step_id"],
                session_id=session_id,
                step_index=s["step_index"],
                title=s["title"],
                description=s.get("description", ""),
                automation_type=s["automation_type"],
                human_instructions=s.get("human_instructions", ""),
                action=s.get("action", {}),
                completion_check=s.get("completion_check", ""),
                extract_fields=s.get("extract_fields", []),
            )

        self.db.update_session(session_id, status="in_progress", total_steps=len(steps))
        self.db.upsert_connection(
            tenant_id=tenant_id,
            provider=provider,
            display_name=business_name,
            metadata={
                "business_name": business_name,
                "email": email,
                "country": country,
                "webhook_url": webhook_endpoint_url,
            },
            next_actions=self._default_next_actions(provider),
        )
        session = self.db.get_session(session_id)
        first_step = self.db.list_steps(session_id)[0] if steps else None
        return {
            "session": session,
            "next_step": first_step,
            "message": (
                f"Session {session_id} created for {provider} setup. "
                f"{len(steps)} steps total. " + (f"First step: {first_step['title']}" if first_step else "No steps.")
            ),
        }

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        session = self.db.get_session(session_id)
        if session is None:
            return None
        session["steps"] = self.db.list_steps(session_id)
        return session

    def list_sessions(
        self,
        tenant_id: str = _DEFAULT_TENANT_ID,
        provider: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.db.list_sessions(tenant_id=self._normalize_tenant_id(tenant_id), provider=provider)

    def start_workflow(
        self,
        provider: str,
        business_name: str,
        email: str,
        country: str = "us",
        webhook_endpoint_url: str = "",
        tenant_id: str = _DEFAULT_TENANT_ID,
        target_offer_slug: str = "",
        selected_slugs: list[str] | None = None,
    ) -> dict[str, Any]:
        setup = self.start_setup(
            provider=provider,
            business_name=business_name,
            email=email,
            country=country,
            webhook_endpoint_url=webhook_endpoint_url,
            tenant_id=tenant_id,
        )
        session = setup["session"]
        first_step = setup.get("next_step")
        run_id = f"{provider}_workflow_{uuid.uuid4().hex[:8]}"
        run = self.db.create_workflow_run(
            run_id=run_id,
            tenant_id=session["tenant_id"],
            provider=provider,
            workflow_type=f"{provider}_onboarding",
            session_id=session["session_id"],
            status="in_progress",
            current_phase="connect",
            target_offer_slug=str(target_offer_slug or "").strip(),
            selected_slugs=[str(slug).strip() for slug in (selected_slugs or []) if str(slug).strip()],
            workflow_metadata={
                "business_name": business_name,
                "email": email,
                "country": country,
                "entry_point": "billing_setup",
            },
        )
        self.db.add_workflow_evidence(
            run["run_id"],
            "workflow_started",
            "Stripe onboarding workflow started.",
            phase="discover",
            payload={
                "provider": provider,
                "business_name": business_name,
                "email": email,
                "session_id": session["session_id"],
            },
        )
        if first_step:
            self.db.add_workflow_evidence(
                run["run_id"],
                "step_ready",
                f"Ready for step: {first_step['title']}",
                phase="connect",
                payload={
                    "step_id": first_step["step_id"],
                    "automation_type": first_step["automation_type"],
                },
            )
        return self.get_workflow_status(run_id=run["run_id"], mock=False)

    def get_workflow_status(
        self,
        run_id: str | None = None,
        tenant_id: str = _DEFAULT_TENANT_ID,
        provider: str = "stripe",
        mock: bool = False,
    ) -> dict[str, Any]:
        tenant_id = self._normalize_tenant_id(tenant_id)
        run = self.db.get_workflow_run(run_id) if run_id else None
        if run is None:
            runs = self.db.list_workflow_runs(tenant_id=tenant_id, provider=provider)
            run = runs[0] if runs else None

        status = self.get_status(tenant_id=tenant_id, provider=provider, include_catalog=True, mock=mock)
        if run is None:
            return {
                "tenant_id": tenant_id,
                "provider": provider,
                "workflow": None,
                "status": status,
                "evidence": [],
            }

        session = self.get_session(run["session_id"]) if run.get("session_id") else None
        evidence = self.db.list_workflow_evidence(run["run_id"])
        checkout_state = self._workflow_checkout_state(evidence)
        current_phase = self._workflow_phase(status, session, checkout_state)
        run_status = self._workflow_run_status(status, session, checkout_state)
        updated_run = (
            self.db.update_workflow_run(
                run["run_id"],
                status=run_status,
                current_phase=current_phase,
            )
            or run
        )
        current_step = None
        if session and session.get("steps"):
            idx = int(session.get("current_step", 0))
            steps = session["steps"]
            if idx < len(steps):
                current_step = steps[idx]
        validation_checkout = updated_run.get("validation_report", {}).get("checkout", {})
        if checkout_state.get("status") == "not_started" and validation_checkout:
            checkout_state = {
                "status": validation_checkout.get("status", "not_started"),
                "checkout_url": validation_checkout.get("checkout_url"),
                "offer_slug": validation_checkout.get("offer_slug"),
                "detail": validation_checkout.get("detail"),
            }
        return {
            "tenant_id": tenant_id,
            "provider": provider,
            "workflow": {
                **updated_run,
                "current_step": current_step,
                "checkout_state": checkout_state,
            },
            "status": status,
            "evidence": evidence,
        }

    def advance_workflow(
        self,
        run_id: str,
        *,
        step_result: dict[str, Any] | None = None,
        human_confirmed: bool = False,
        mock: bool = False,
    ) -> dict[str, Any]:
        run = self.db.get_workflow_run(run_id)
        if run is None:
            raise ValueError(f"Workflow run {run_id!r} not found.")
        session = self.get_session(run["session_id"]) if run.get("session_id") else None
        if session is None:
            raise ValueError(f"Workflow run {run_id!r} is missing its setup session.")

        steps = session.get("steps", [])
        current_idx = int(session.get("current_step", 0))
        current_step = steps[current_idx] if current_idx < len(steps) else None
        result = self.advance_step(
            session_id=session["session_id"],
            step_result=step_result,
            human_confirmed=human_confirmed,
        )
        phase = self._phase_from_step(current_step)
        if result.get("awaiting_human"):
            self.db.add_workflow_evidence(
                run_id,
                "human_gate",
                f"Human action required: {current_step['title'] if current_step else 'Unknown step'}",
                phase=phase,
                status="awaiting_human",
                payload={
                    "instructions": result.get("human_instructions", ""),
                    "step_id": current_step["step_id"] if current_step else "",
                },
            )
        elif current_step:
            self.db.add_workflow_evidence(
                run_id,
                "step_completed",
                f"Completed step: {current_step['title']}",
                phase=phase,
                payload={
                    "step_id": current_step["step_id"],
                    "automation_type": current_step["automation_type"],
                    "step_result": self._redact_values(step_result or {}),
                    "human_confirmed": human_confirmed,
                },
            )
        if result.get("next_step"):
            self.db.add_workflow_evidence(
                run_id,
                "step_ready",
                f"Ready for step: {result['next_step']['title']}",
                phase=self._phase_from_step(result["next_step"]),
                payload={
                    "step_id": result["next_step"]["step_id"],
                    "automation_type": result["next_step"]["automation_type"],
                },
            )
        elif result.get("session", {}).get("status") == "complete":
            self.db.add_workflow_evidence(
                run_id,
                "setup_completed",
                "The browser-guided setup session completed.",
                phase="configure",
                payload={"session_id": session["session_id"]},
            )
        return self.get_workflow_status(run_id=run_id, tenant_id=run["tenant_id"], provider=run["provider"], mock=mock)

    def validate_workflow(
        self,
        run_id: str,
        *,
        apply_catalog_sync: bool = False,
        selected_slugs: list[str] | None = None,
        target_offer_slug: str | None = None,
        checkout_completed: bool = False,
        mock: bool = False,
    ) -> dict[str, Any]:
        run = self.db.get_workflow_run(run_id)
        if run is None:
            raise ValueError(f"Workflow run {run_id!r} not found.")

        tenant_id = run["tenant_id"]
        provider = run["provider"]
        selected = [
            str(slug).strip() for slug in (selected_slugs or run.get("selected_slugs") or []) if str(slug).strip()
        ]
        target_slug = str(target_offer_slug or run.get("target_offer_slug") or "").strip()

        catalog_result = None
        if apply_catalog_sync:
            catalog_result = self.sync_catalog(
                tenant_id=tenant_id,
                provider=provider,
                apply=True,
                selected_slugs=selected,
                mock=mock,
            )
            self.db.add_workflow_evidence(
                run_id,
                "catalog_sync",
                "Catalog synced during workflow validation.",
                phase="catalog",
                payload={
                    "status": catalog_result.get("status"),
                    "offer_count": catalog_result.get("offer_count", 0),
                    "selected_slugs": selected,
                },
            )

        verification = self.verify_setup(provider=provider, tenant_id=tenant_id, mock=mock)
        checkout_result: dict[str, Any] | None = None
        if checkout_completed:
            checkout_result = {
                "status": "completed",
                "detail": "Operator confirmed the hosted Stripe test checkout completed.",
            }
            self.db.add_workflow_evidence(
                run_id,
                "checkout_completed",
                "Hosted Stripe checkout completed by the operator.",
                phase="validate",
                status="confirmed",
                payload=checkout_result,
            )
        else:
            checkout_result = self.create_checkout_validation(
                tenant_id=tenant_id,
                provider=provider,
                target_offer_slug=target_slug,
                mock=mock,
            )
            if checkout_result.get("status") != "not_ready":
                self.db.add_workflow_evidence(
                    run_id,
                    "checkout_session_created",
                    "Hosted Stripe checkout session created.",
                    phase="validate",
                    status="awaiting_human",
                    payload=checkout_result,
                )

        validation_report = {
            "verification": verification,
            "catalog_sync": catalog_result or {},
            "checkout": checkout_result or {},
            "last_validated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.db.add_workflow_evidence(
            run_id,
            "readiness_report",
            "Workflow validation report generated.",
            phase="validate",
            payload={
                "ready": verification["summary"]["ready"],
                "failed": verification["summary"]["failed"],
                "checkout_status": (checkout_result or {}).get("status", ""),
            },
        )
        self.db.update_workflow_run(
            run_id,
            selected_slugs=selected or run.get("selected_slugs", []),
            target_offer_slug=target_slug or run.get("target_offer_slug", ""),
            validation_report=validation_report,
        )
        return self.get_workflow_status(run_id=run_id, tenant_id=tenant_id, provider=provider, mock=mock)

    # -- step execution ------------------------------------------------------

    def advance_step(
        self,
        session_id: str,
        step_result: dict[str, Any] | None = None,
        human_confirmed: bool = False,
    ) -> dict[str, Any]:
        session = self.db.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id!r} not found")

        steps = self.db.list_steps(session_id)
        current_idx = session.get("current_step", 0)
        if current_idx >= len(steps):
            return {"session": session, "next_step": None, "message": "Setup complete."}

        current_step = steps[current_idx]
        if current_step["automation_type"] == "human_required" and not human_confirmed:
            self.db.update_session(session_id, status="awaiting_human")
            return {
                "session": self.db.get_session(session_id),
                "next_step": current_step,
                "awaiting_human": True,
                "human_instructions": current_step["human_instructions"],
                "message": (
                    f"Step '{current_step['title']}' requires operator action. "
                    "Call advance_step with human_confirmed=True when done."
                ),
            }

        self.db.update_step(current_step["step_id"], status="completed", result_data=step_result or {})

        extracted = session.get("extracted_credentials", {})
        if step_result:
            for field in current_step.get("extract_fields", []):
                if step_result.get(field):
                    extracted[field] = step_result[field]

        if current_step.get("action", {}).get("tool") == "internal_store_credentials":
            provider = current_step["action"]["args"].get("provider", session["provider"])
            self.store_credentials(
                provider=provider,
                credentials=extracted,
                session_id=session_id,
                tenant_id=session.get("tenant_id", _DEFAULT_TENANT_ID),
                write_to_env=False,
            )

        next_idx = current_idx + 1
        self.db.update_session(
            session_id,
            current_step=next_idx,
            status="in_progress",
            extracted_credentials=extracted,
        )
        next_step = steps[next_idx] if next_idx < len(steps) else None
        if next_step is None:
            self.db.update_session(session_id, status="complete")

        return {
            "session": self.db.get_session(session_id),
            "next_step": next_step,
            "extracted_credentials": self._redact_values(extracted),
            "message": (
                f"Step {current_idx + 1}/{len(steps)} complete. "
                + (f"Next: {next_step['title']}" if next_step else "All steps complete!")
            ),
        }

    def mark_step_failed(self, session_id: str, error: str) -> dict[str, Any] | None:
        session = self.db.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id!r} not found")
        steps = self.db.list_steps(session_id)
        current_idx = session.get("current_step", 0)
        if current_idx < len(steps):
            self.db.update_step(steps[current_idx]["step_id"], status="failed", error=error)
        self.db.update_session(session_id, status="failed", notes=error)
        return self.get_session(session_id)

    # -- credential management -----------------------------------------------

    def store_credentials(
        self,
        provider: str,
        credentials: dict[str, str],
        session_id: str | None = None,
        tenant_id: str = _DEFAULT_TENANT_ID,
        push_to_vercel: bool = False,
        write_to_env: bool = False,
    ) -> dict[str, str]:
        tenant_id = self._normalize_tenant_id(tenant_id)
        written: dict[str, str] = {}

        for logical_name, value in credentials.items():
            if not value:
                continue
            self.db.store_secret(tenant_id, provider, logical_name, value)
            written[logical_name] = self._redact(value)

        if write_to_env:
            self.credential_store.write_credentials(provider, credentials, push_to_vercel=push_to_vercel)

        if session_id:
            session = self.db.get_session(session_id)
            if session:
                existing = session.get("extracted_credentials", {})
                existing.update(credentials)
                self.db.update_session(session_id, extracted_credentials=existing)

        connection = self.db.get_connection(tenant_id, provider) or {}
        self.db.upsert_connection(
            tenant_id=tenant_id,
            provider=provider,
            display_name=connection.get("display_name", ""),
            mode=connection.get("mode", "test"),
            account_status="credentials_captured",
            readiness_status=connection.get("readiness_status", "needs_attention"),
            provider_account_id=connection.get("provider_account_id", ""),
            metadata=connection.get("metadata", {}),
            capabilities=connection.get("capabilities", []),
            missing_capabilities=connection.get("missing_capabilities", []),
            next_actions=connection.get("next_actions", self._default_next_actions(provider)),
            connected_at=connection.get("connected_at"),
            last_verified_at=connection.get("last_verified_at"),
        )
        return written

    def get_provider_credentials(
        self,
        provider: str,
        tenant_id: str = _DEFAULT_TENANT_ID,
    ) -> dict[str, str | None]:
        tenant_id = self._normalize_tenant_id(tenant_id)
        from instruments.custom.payment_account_setup.credential_store import PROVIDER_ENV_MAP

        env_map = PROVIDER_ENV_MAP.get(provider.lower(), {})
        result: dict[str, str | None] = {}
        for logical, env_name in env_map.items():
            val = self.db.read_secret(tenant_id, provider, logical) or self.credential_store.read_credential(env_name)
            result[logical] = self._redact(val) if val else None
        return result

    # -- billing copilot status ----------------------------------------------

    def get_status(
        self,
        tenant_id: str = _DEFAULT_TENANT_ID,
        provider: str = "stripe",
        include_catalog: bool = False,
        mock: bool = False,
    ) -> dict[str, Any]:
        tenant_id = self._normalize_tenant_id(tenant_id)
        checks_payload = self.verify_setup(provider=provider, tenant_id=tenant_id, persist=False, mock=mock)
        sessions = self.list_sessions(tenant_id=tenant_id, provider=provider)
        active_session = next(
            (session for session in sessions if session.get("status") in {"pending", "in_progress", "awaiting_human"}),
            None,
        )
        connection = self.db.get_connection(tenant_id, provider) or {
            "tenant_id": tenant_id,
            "provider": provider,
            "display_name": "",
            "mode": "test",
            "account_status": "not_connected",
            "readiness_status": "needs_attention",
            "metadata": {},
            "capabilities": [],
            "missing_capabilities": [],
            "next_actions": self._default_next_actions(provider),
        }
        payload: dict[str, Any] = {
            "tenant_id": tenant_id,
            "provider": provider,
            "connection": connection,
            "credentials": self.get_provider_credentials(provider, tenant_id=tenant_id),
            "checks": checks_payload["checks"],
            "summary": checks_payload["summary"],
            "next_actions": checks_payload["next_actions"],
            "journey": self._customer_journey(provider, checks_payload["checks"], active_session, connection),
            "active_session": self.get_session(active_session["session_id"]) if active_session else None,
            "recent_sessions": sessions[:5],
            "guidance_sections": self._guidance_sections(provider, checks_payload["checks"]),
            "process_playbooks": self._process_playbooks(provider),
        }
        if include_catalog:
            payload["catalog"] = self.get_catalog(tenant_id=tenant_id, provider=provider)
        return payload

    def verify_setup(
        self,
        provider: str,
        tenant_id: str = _DEFAULT_TENANT_ID,
        persist: bool = True,
        mock: bool = False,
    ) -> dict[str, Any]:
        tenant_id = self._normalize_tenant_id(tenant_id)
        provider = provider.lower().strip()
        if provider != "stripe":
            return {
                "status": "not_implemented",
                "provider": provider,
                "checks": [],
                "summary": {
                    "ready": False,
                    "passed": 0,
                    "failed": 1,
                    "message": f"{provider} copilot not implemented yet.",
                },
                "next_actions": [
                    {"id": "provider_rollout", "title": f"{provider.title()} support is planned after Stripe."}
                ],
            }

        credentials = self._read_raw_credentials(provider, tenant_id)
        webhook_url = self._default_webhook_url(provider)
        checks: list[dict[str, Any]] = [
            self._check(
                "api_key", bool(credentials.get("stripe_secret_key")), "API key captured", "Add your Stripe secret key."
            ),
            self._check(
                "webhook_secret",
                bool(credentials.get("stripe_webhook_secret")),
                "Webhook secret captured",
                "Add your Stripe webhook signing secret.",
            ),
        ]
        next_actions = self._default_next_actions(provider)
        account: dict[str, Any] = {}
        endpoints: list[dict[str, Any]] = []
        mode = "test"
        api_ok = False

        if credentials.get("stripe_secret_key"):
            api_ok, account, endpoints, mode, auth_error = self._fetch_stripe_remote_state(
                credentials["stripe_secret_key"],
                credentials.get("stripe_webhook_secret"),
                mock=mock,
            )
            checks.append(
                self._check(
                    "api_auth",
                    api_ok,
                    "Stripe API authentication succeeded",
                    auth_error or "Could not authenticate with Stripe.",
                )
            )
            if api_ok:
                details_submitted = bool(account.get("details_submitted"))
                charges_enabled = bool(account.get("charges_enabled"))
                payouts_enabled = bool(account.get("payouts_enabled"))
                requirements_due = account.get("requirements", {}).get("currently_due", []) or []
                checks.extend(
                    [
                        self._check(
                            "business_profile",
                            details_submitted,
                            "Business profile appears submitted in Stripe.",
                            "Complete Stripe business profile and KYC details.",
                        ),
                        self._check(
                            "charges_enabled",
                            charges_enabled,
                            "Payments are enabled for this Stripe account.",
                            "Finish Stripe requirements until charges are enabled.",
                        ),
                        self._check(
                            "payouts_enabled",
                            payouts_enabled,
                            "Payouts are enabled.",
                            "Configure bank account and payout settings in Stripe.",
                        ),
                        self._check(
                            "requirements_due",
                            len(requirements_due) == 0,
                            "No current Stripe requirements are due.",
                            f"Stripe still requires: {', '.join(requirements_due)}"
                            if requirements_due
                            else "Stripe still shows pending requirements.",
                        ),
                    ]
                )
                endpoint = next((item for item in endpoints if item.get("url") == webhook_url), None)
                checks.append(
                    self._check(
                        "webhook_endpoint",
                        endpoint is not None,
                        f"Webhook endpoint registered for {webhook_url}.",
                        f"Register {webhook_url} in Stripe webhooks.",
                    )
                )
                catalog_diff = self.diff_catalog(tenant_id=tenant_id, provider=provider, mock=mock)
                # In mock mode, price-replacement mismatches are expected (mock prices drift);
                # only count offers that have no product at all as missing.
                if mock:
                    missing_offers = [
                        item for item in catalog_diff["offers"] if item["recommended_action"] in ("create", "missing")
                    ]
                else:
                    missing_offers = [item for item in catalog_diff["offers"] if item["recommended_action"] != "ready"]
                checks.append(
                    self._check(
                        "catalog_sync",
                        len(missing_offers) == 0,
                        "Catalog offers are present in Stripe.",
                        f"{len(missing_offers)} catalog offers still need sync or review.",
                    )
                )
                checks.append(
                    self._check(
                        "test_checkout_ready",
                        any(
                            item.get("monthly_price_id") or item.get("setup_price_id")
                            for item in catalog_diff["offers"]
                        ),
                        "At least one billable price is ready for test checkout.",
                        "Sync at least one paid offer before testing checkout.",
                    )
                )

        passed = sum(1 for check in checks if check["ok"])
        failed = len(checks) - passed
        ready = failed == 0 and len(checks) > 0
        next_actions = [self._action_from_check(check) for check in checks if not check["ok"]]
        if not next_actions:
            next_actions = [
                {
                    "id": "ready",
                    "title": "Stripe setup is healthy.",
                    "detail": "You can now validate live checkout and ongoing catalog updates.",
                }
            ]

        metadata = {
            "webhook_url": webhook_url,
            "mode": mode,
            "business_name": account.get("business_profile", {}).get("name")
            or account.get("settings", {}).get("dashboard", {}).get("display_name", ""),
            "requirements_due": account.get("requirements", {}).get("currently_due", []) if api_ok else [],
            "charges_enabled": bool(account.get("charges_enabled")) if api_ok else False,
            "payouts_enabled": bool(account.get("payouts_enabled")) if api_ok else False,
        }

        summary = {
            "ready": ready,
            "passed": passed,
            "failed": failed,
            "message": "Stripe billing admin is ready." if ready else "Stripe billing admin still needs attention.",
        }

        if persist:
            self.db.upsert_connection(
                tenant_id=tenant_id,
                provider=provider,
                display_name=metadata.get("business_name", ""),
                mode=mode,
                account_status="connected" if api_ok else "not_connected",
                readiness_status="ready" if ready else "needs_attention",
                provider_account_id=account.get("id", ""),
                metadata=metadata,
                capabilities=[check["id"] for check in checks if check["ok"]],
                missing_capabilities=[check["id"] for check in checks if not check["ok"]],
                next_actions=next_actions,
                connected_at=datetime.now(timezone.utc).isoformat() if api_ok else None,
                last_verified_at=datetime.now(timezone.utc).isoformat(),
            )

        return {
            "status": "ok" if ready else "attention",
            "provider": provider,
            "checks": checks,
            "summary": summary,
            "next_actions": next_actions,
            "metadata": metadata,
        }

    # -- catalog management --------------------------------------------------

    def get_catalog(
        self,
        tenant_id: str = _DEFAULT_TENANT_ID,
        provider: str = "stripe",
    ) -> dict[str, Any]:
        tenant_id = self._normalize_tenant_id(tenant_id)
        templates = {offer.slug: offer for offer in load_commercial_catalog()}
        stored = {item["slug"]: item for item in self.db.list_catalog_items(tenant_id, provider)}
        offers: list[dict[str, Any]] = []

        for slug, offer in templates.items():
            record = stored.get(slug)
            merged = offer.to_dict()
            if record:
                merged["name"] = record.get("name") or merged["name"]
                merged["tagline"] = record.get("tagline") or merged["tagline"]
                merged["description"] = record.get("description") or merged["description"]
                merged["billing_mode"] = record.get("billing_mode") or merged["billing_mode"]
                merged["monthly_price_usd"] = float(record.get("monthly_price_usd", merged["monthly_price_usd"]) or 0)
                merged["setup_price_usd"] = float(record.get("setup_price_usd", merged["setup_price_usd"]) or 0)
                merged["active"] = bool(record.get("active", merged["active"]))
            merged["source_kind"] = record.get("source_kind", "template") if record else "template"
            merged["sync_status"] = record.get("sync_status", "pending") if record else "pending"
            merged["provider_product_id"] = record.get("provider_product_id") if record else None
            merged["monthly_price_id"] = record.get("provider_monthly_price_id") if record else None
            merged["setup_price_id"] = record.get("provider_setup_price_id") if record else None
            merged["provider_metadata"] = record.get("provider_metadata", {}) if record else {}
            merged["is_free"] = offer.is_free
            merged["is_custom_quote"] = offer.is_custom_quote
            offers.append(merged)
            if not record:
                self.db.upsert_catalog_item(
                    tenant_id=tenant_id,
                    provider=provider,
                    catalog_family=offer.catalog_family,
                    slug=offer.slug,
                    name=offer.name,
                    tagline=offer.tagline,
                    description=offer.description,
                    billing_mode=offer.billing_mode,
                    monthly_price_usd=offer.monthly_price_usd,
                    setup_price_usd=offer.setup_price_usd,
                    active=offer.active,
                    source_kind="template",
                    source_path=offer.source_path,
                    metadata=offer.metadata,
                    sync_status="pending",
                )

        return {
            "tenant_id": tenant_id,
            "provider": provider,
            "offer_count": len(offers),
            "offers": sorted(offers, key=lambda item: (item["catalog_family"], item["slug"])),
        }

    def update_catalog_offer(
        self,
        tenant_id: str = _DEFAULT_TENANT_ID,
        provider: str = "stripe",
        slug: str = "",
        *,
        active: bool | None = None,
        monthly_price_usd: float | None = None,
        setup_price_usd: float | None = None,
        name: str | None = None,
        tagline: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        tenant_id = self._normalize_tenant_id(tenant_id)
        slug = str(slug).strip()
        if not slug:
            raise ValueError("Catalog slug is required.")

        catalog = self.get_catalog(tenant_id=tenant_id, provider=provider)
        offer = next((item for item in catalog["offers"] if item["slug"] == slug), None)
        if offer is None:
            raise ValueError(f"Catalog offer {slug!r} not found.")

        template = next((item for item in load_commercial_catalog() if item.slug == slug), None)
        if template is None:
            raise ValueError(f"Template offer {slug!r} not found.")

        next_monthly = float(offer["monthly_price_usd"] if monthly_price_usd is None else monthly_price_usd)
        next_setup = float(offer["setup_price_usd"] if setup_price_usd is None else setup_price_usd)
        if next_monthly < 0 or next_setup < 0:
            raise ValueError("Catalog prices cannot be negative.")

        next_active = bool(offer["active"] if active is None else active)
        next_name = str(offer["name"] if name is None else name).strip()
        next_tagline = str(offer["tagline"] if tagline is None else tagline).strip()
        next_description = str(offer["description"] if description is None else description).strip()

        customized = any(
            [
                next_active != bool(template.active),
                next_name != template.name,
                next_tagline != template.tagline,
                next_description != template.description,
                next_monthly != float(template.monthly_price_usd),
                next_setup != float(template.setup_price_usd),
            ]
        )

        updated = self.db.upsert_catalog_item(
            tenant_id=tenant_id,
            provider=provider,
            catalog_family=offer["catalog_family"],
            slug=slug,
            name=next_name,
            tagline=next_tagline,
            description=next_description,
            billing_mode=offer["billing_mode"],
            monthly_price_usd=next_monthly,
            setup_price_usd=next_setup,
            active=next_active,
            source_kind="customized" if customized else "template",
            source_path=offer["source_path"],
            metadata=offer["metadata"],
            provider_product_id=offer.get("provider_product_id"),
            provider_monthly_price_id=offer.get("monthly_price_id"),
            provider_setup_price_id=offer.get("setup_price_id"),
            sync_status="pending" if next_active else "inactive",
            provider_metadata=offer.get("provider_metadata", {}),
            last_synced_at=offer.get("last_synced_at"),
        )
        refreshed = self.get_catalog(tenant_id=tenant_id, provider=provider)
        refreshed_offer = next(item for item in refreshed["offers"] if item["slug"] == slug)
        return {
            "status": "updated",
            "provider": provider,
            "tenant_id": tenant_id,
            "offer": refreshed_offer,
            "record": updated,
        }

    def diff_catalog(
        self,
        tenant_id: str = _DEFAULT_TENANT_ID,
        provider: str = "stripe",
        mock: bool = False,
    ) -> dict[str, Any]:
        tenant_id = self._normalize_tenant_id(tenant_id)
        catalog = self.get_catalog(tenant_id=tenant_id, provider=provider)
        remote_products: dict[str, dict[str, Any]] = {}
        remote_prices: list[dict[str, Any]] = []

        if provider == "stripe":
            credentials = self._read_raw_credentials(provider, tenant_id)
            if credentials.get("stripe_secret_key"):
                try:
                    client = self._stripe_provider(
                        api_key=credentials["stripe_secret_key"],
                        webhook_secret=credentials.get("stripe_webhook_secret"),
                        mock=mock,
                    )
                    remote_products = {item["id"]: item for item in client.list_products(active=None)}
                    remote_prices = client.list_prices(active=None)
                except Exception as exc:
                    logger.warning("Catalog diff could not reach Stripe: %s", exc)

        offers: list[dict[str, Any]] = []
        for offer in catalog["offers"]:
            prices = [price for price in remote_prices if price.get("product") == offer["product_id"]]
            expected_monthly_amount = round(float(offer["monthly_price_usd"]) * 100)
            expected_setup_amount = round(float(offer["setup_price_usd"]) * 100)
            monthly_price = next(
                (
                    price
                    for price in prices
                    if price.get("unit_amount") == expected_monthly_amount
                    and (price.get("recurring") or {}).get("interval") == "month"
                ),
                None,
            )
            setup_price = next(
                (
                    price
                    for price in prices
                    if price.get("unit_amount") == expected_setup_amount and not price.get("recurring")
                ),
                None,
            )
            product_exists = offer["product_id"] in remote_products or bool(offer.get("provider_product_id"))
            monthly_price_matches = bool(monthly_price) if offer.get("monthly_lookup_key") else True
            setup_price_matches = bool(setup_price) if offer.get("setup_lookup_key") else True
            recommended_action = "ready"
            if not offer.get("active", True):
                recommended_action = "inactive"
            elif not product_exists and not offer["is_free"] and not offer["is_custom_quote"]:
                recommended_action = "create_product"
            elif offer.get("monthly_lookup_key") and not monthly_price_matches:
                recommended_action = (
                    "replace_monthly_price" if prices or offer.get("monthly_price_id") else "create_monthly_price"
                )
            elif offer.get("setup_lookup_key") and not setup_price_matches:
                recommended_action = (
                    "replace_setup_price" if prices or offer.get("setup_price_id") else "create_setup_price"
                )

            offers.append(
                {
                    **offer,
                    "product_exists": product_exists,
                    "monthly_price_matches": monthly_price_matches,
                    "setup_price_matches": setup_price_matches,
                    "monthly_price_id": monthly_price.get("id") if monthly_price else offer.get("monthly_price_id"),
                    "setup_price_id": setup_price.get("id") if setup_price else offer.get("setup_price_id"),
                    "recommended_action": recommended_action,
                }
            )

        return {"tenant_id": tenant_id, "provider": provider, "offers": offers}

    def sync_catalog(
        self,
        tenant_id: str = _DEFAULT_TENANT_ID,
        provider: str = "stripe",
        apply: bool = False,
        selected_slugs: list[str] | None = None,
        mock: bool = False,
    ) -> dict[str, Any]:
        tenant_id = self._normalize_tenant_id(tenant_id)
        diff = self.diff_catalog(tenant_id=tenant_id, provider=provider, mock=mock)
        selected = set(selected_slugs or [])
        offers = [item for item in diff["offers"] if not selected or item["slug"] in selected]

        if provider != "stripe":
            return {"status": "not_implemented", "provider": provider, "offers": offers}

        credentials = self._read_raw_credentials(provider, tenant_id)
        if not credentials.get("stripe_secret_key"):
            return {"status": "missing_credentials", "provider": provider, "offers": offers}

        if not apply:
            return {"status": "dry_run", "provider": provider, "offers": offers}

        client = self._stripe_provider(
            api_key=credentials["stripe_secret_key"],
            webhook_secret=credentials.get("stripe_webhook_secret"),
            mock=mock,
        )
        synced: list[dict[str, Any]] = []
        for offer in offers:
            if not offer.get("active", True):
                self.db.upsert_catalog_item(
                    tenant_id=tenant_id,
                    provider=provider,
                    catalog_family=offer["catalog_family"],
                    slug=offer["slug"],
                    name=offer["name"],
                    tagline=offer["tagline"],
                    description=offer["description"],
                    billing_mode=offer["billing_mode"],
                    monthly_price_usd=float(offer["monthly_price_usd"]),
                    setup_price_usd=float(offer["setup_price_usd"]),
                    active=False,
                    source_kind=offer.get("source_kind", "customized"),
                    source_path=offer["source_path"],
                    metadata=offer["metadata"],
                    provider_product_id=offer.get("provider_product_id"),
                    provider_monthly_price_id=offer.get("monthly_price_id"),
                    provider_setup_price_id=offer.get("setup_price_id"),
                    sync_status="inactive",
                    provider_metadata=offer.get("provider_metadata", {}),
                    last_synced_at=offer.get("last_synced_at"),
                )
                synced.append({**offer, "sync_status": "inactive"})
                continue
            if offer["is_free"] or offer["is_custom_quote"]:
                self.db.upsert_catalog_item(
                    tenant_id=tenant_id,
                    provider=provider,
                    catalog_family=offer["catalog_family"],
                    slug=offer["slug"],
                    name=offer["name"],
                    tagline=offer["tagline"],
                    description=offer["description"],
                    billing_mode=offer["billing_mode"],
                    monthly_price_usd=float(offer["monthly_price_usd"]),
                    setup_price_usd=float(offer["setup_price_usd"]),
                    active=bool(offer["active"]),
                    source_kind="template",
                    source_path=offer["source_path"],
                    metadata=offer["metadata"],
                    sync_status="ready",
                )
                synced.append({**offer, "sync_status": "ready"})
                continue

            product_id = offer["product_id"]
            monthly_price_id = offer.get("monthly_price_id")
            setup_price_id = offer.get("setup_price_id")
            if not offer["product_exists"]:
                product = client.create_product(
                    name=offer["name"],
                    description=offer["description"],
                    metadata=offer["metadata"],
                )
                product_id = product.get("id", product_id)
            if offer.get("monthly_lookup_key") and not offer.get("monthly_price_matches", False):
                price = client.create_price(product_id, round(float(offer["monthly_price_usd"]) * 100), "usd", "month")
                monthly_price_id = price.get("id")
            if offer.get("setup_lookup_key") and not offer.get("setup_price_matches", False):
                price = client.create_price(product_id, round(float(offer["setup_price_usd"]) * 100))
                setup_price_id = price.get("id")

            self.db.upsert_catalog_item(
                tenant_id=tenant_id,
                provider=provider,
                catalog_family=offer["catalog_family"],
                slug=offer["slug"],
                name=offer["name"],
                tagline=offer["tagline"],
                description=offer["description"],
                billing_mode=offer["billing_mode"],
                monthly_price_usd=float(offer["monthly_price_usd"]),
                setup_price_usd=float(offer["setup_price_usd"]),
                active=bool(offer["active"]),
                source_kind=offer.get("source_kind", "template"),
                source_path=offer["source_path"],
                metadata=offer["metadata"],
                provider_product_id=product_id,
                provider_monthly_price_id=monthly_price_id,
                provider_setup_price_id=setup_price_id,
                sync_status="ready",
                provider_metadata={"synced_via": "billing_setup_manager"},
                last_synced_at=datetime.now(timezone.utc).isoformat(),
            )
            synced.append(
                {
                    **offer,
                    "product_id": product_id,
                    "monthly_price_id": monthly_price_id,
                    "setup_price_id": setup_price_id,
                    "sync_status": "ready",
                }
            )

        return {"status": "synced", "provider": provider, "offer_count": len(synced), "offers": synced}

    def create_checkout_validation(
        self,
        *,
        tenant_id: str = _DEFAULT_TENANT_ID,
        provider: str = "stripe",
        target_offer_slug: str = "",
        mock: bool = False,
    ) -> dict[str, Any]:
        tenant_id = self._normalize_tenant_id(tenant_id)
        credentials = self._read_raw_credentials(provider, tenant_id)
        if provider != "stripe" or not credentials.get("stripe_secret_key"):
            return {"status": "not_ready", "detail": "Stripe credentials are required before checkout validation."}

        diff = self.diff_catalog(tenant_id=tenant_id, provider=provider, mock=mock)
        candidates = [
            offer
            for offer in diff["offers"]
            if offer.get("active", True)
            and not offer.get("is_free")
            and not offer.get("is_custom_quote")
            and (offer.get("monthly_price_id") or offer.get("setup_price_id"))
        ]
        if target_offer_slug:
            candidates = [offer for offer in candidates if offer["slug"] == target_offer_slug]
        if not candidates:
            return {
                "status": "not_ready",
                "detail": "Sync at least one paid offer before running hosted checkout validation.",
            }

        offer = candidates[0]
        price_id = offer.get("monthly_price_id") or offer.get("setup_price_id")
        if not price_id:
            return {"status": "not_ready", "detail": "No Stripe price is available for the selected offer."}

        client = self._stripe_provider(
            api_key=credentials["stripe_secret_key"],
            webhook_secret=credentials.get("stripe_webhook_secret"),
            mock=mock,
        )
        connection = self.db.get_connection(tenant_id, provider) or {}
        metadata = connection.get("metadata", {})
        customer = client.create_customer(
            email=metadata.get("email") or "billing@example.com",
            name=metadata.get("business_name") or connection.get("display_name") or "Mahoosuc tenant",
            metadata={"tenant_id": tenant_id, "offer_slug": offer["slug"]},
        )
        checkout = client.create_checkout_session(
            price_id=price_id,
            customer_id=customer["id"],
            mode="subscription" if offer.get("monthly_price_id") else "payment",
            success_url=os.environ.get(
                "STRIPE_CHECKOUT_SUCCESS_URL",
                "http://localhost:6274/billing/setup?checkout=success",
            ),
            cancel_url=os.environ.get(
                "STRIPE_CHECKOUT_CANCEL_URL",
                "http://localhost:6274/billing/setup?checkout=cancelled",
            ),
            metadata={"tenant_id": tenant_id, "offer_slug": offer["slug"]},
        )
        return {
            "status": "awaiting_human_completion",
            "offer_slug": offer["slug"],
            "price_id": price_id,
            "customer_id": customer["id"],
            "checkout_session_id": checkout.get("id"),
            "checkout_url": checkout.get("url"),
            "detail": "Open the hosted Stripe checkout URL and complete the test checkout, then confirm it in the workflow.",
        }

    # -- internal helpers ----------------------------------------------------

    def _normalize_tenant_id(self, tenant_id: str | None) -> str:
        return (tenant_id or _DEFAULT_TENANT_ID).strip() or _DEFAULT_TENANT_ID

    def _default_webhook_url(self, provider: str) -> str:
        if provider == "stripe":
            return os.environ.get("STRIPE_WEBHOOK_ENDPOINT_URL", "http://localhost:6274/api/stripe/webhook")
        return "http://localhost:6274/api/webhook"

    def _redact(self, value: str | None) -> str:
        if not value:
            return ""
        return f"{value[:8]}..." if len(value) > 8 else "***"

    def _redact_values(self, values: dict[str, Any]) -> dict[str, Any]:
        return {key: self._redact(str(value)) if isinstance(value, str) else value for key, value in values.items()}

    def _check(self, check_id: str, ok: bool, success_detail: str, failure_detail: str) -> dict[str, Any]:
        return {"id": check_id, "ok": ok, "detail": success_detail if ok else failure_detail}

    def _action_from_check(self, check: dict[str, Any]) -> dict[str, str]:
        return {"id": check["id"], "title": check["id"].replace("_", " ").title(), "detail": str(check["detail"])}

    def _phase_from_step(self, step: dict[str, Any] | None) -> str:
        if not step:
            return "discover"
        title = str(step.get("title", "")).lower()
        if "api key" in title or "webhook" in title or "credential" in title:
            return "connect"
        if "catalog" in title:
            return "catalog"
        if any(token in title for token in ("verification", "2fa", "captcha", "identity")):
            return "configure"
        return "configure"

    def _workflow_checkout_state(self, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        created = next(
            (item for item in reversed(evidence) if item.get("evidence_type") == "checkout_session_created"), None
        )
        completed = next(
            (item for item in reversed(evidence) if item.get("evidence_type") == "checkout_completed"), None
        )
        if completed:
            return {"status": "completed", **completed.get("payload", {})}
        if created:
            return {"status": "awaiting_human_completion", **created.get("payload", {})}
        return {"status": "not_started"}

    def _workflow_phase(
        self,
        status_payload: dict[str, Any],
        session: dict[str, Any] | None,
        checkout_state: dict[str, Any],
    ) -> str:
        journey_phase = status_payload.get("journey", {}).get("current_stage") or "discover"
        if checkout_state.get("status") == "awaiting_human_completion":
            return "validate"
        if session and session.get("status") == "complete" and journey_phase == "operate":
            return "validate" if checkout_state.get("status") != "completed" else "operate"
        return str(journey_phase)

    def _workflow_run_status(
        self,
        status_payload: dict[str, Any],
        session: dict[str, Any] | None,
        checkout_state: dict[str, Any],
    ) -> str:
        if checkout_state.get("status") == "completed" and status_payload.get("summary", {}).get("ready"):
            return "completed"
        if checkout_state.get("status") == "awaiting_human_completion":
            return "awaiting_human"
        if session and session.get("status") == "awaiting_human":
            return "awaiting_human"
        if status_payload.get("summary", {}).get("ready"):
            return "ready"
        return "in_progress"

    def _default_next_actions(self, provider: str) -> list[dict[str, str]]:
        if provider == "stripe":
            return [
                {
                    "id": "capture_keys",
                    "title": "Capture Stripe test API key",
                    "detail": "Open the Stripe developer dashboard and copy the test secret key.",
                },
                {
                    "id": "configure_webhook",
                    "title": "Register webhook endpoint",
                    "detail": f"Point Stripe to {self._default_webhook_url(provider)} and save the signing secret.",
                },
                {
                    "id": "sync_catalog",
                    "title": "Review catalog offers",
                    "detail": "Compare your tenant catalog against the Mahoosuc templates before syncing products and prices.",
                },
            ]
        return [
            {
                "id": "provider_pending",
                "title": f"{provider.title()} support pending",
                "detail": "Stripe is the primary guided provider today.",
            }
        ]

    def _guidance_sections(self, provider: str, checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        failures = [check for check in checks if not check["ok"]]
        return [
            {
                "id": "connection",
                "title": "Connection",
                "summary": "Store your tenant-owned API key and webhook secret. Mahoosuc reads readiness from that connection.",
            },
            {
                "id": "guided_setup",
                "title": "Guided Setup",
                "summary": "Use the step-by-step setup session to walk through Stripe Dashboard tasks and regulated checkpoints.",
            },
            {
                "id": "health",
                "title": "Health",
                "summary": "Re-run verification after dashboard changes. "
                + (
                    "Current blockers: " + "; ".join(check["detail"] for check in failures[:2])
                    if failures
                    else "Everything currently looks healthy."
                ),
            },
            {
                "id": "catalog",
                "title": "Catalog",
                "summary": "Start from Mahoosuc templates, then sync only the offers you want in the tenant Stripe account.",
            },
        ]

    def _customer_journey(
        self,
        provider: str,
        checks: list[dict[str, Any]],
        active_session: dict[str, Any] | None,
        connection: dict[str, Any],
    ) -> dict[str, Any]:
        if provider != "stripe":
            return {"current_stage": "unsupported", "stages": []}

        check_map = {check["id"]: bool(check["ok"]) for check in checks}
        has_active_session = bool(active_session)
        stages = [
            {
                "id": "discover",
                "title": "Discover",
                "status": "complete",
                "goal": "Understand what Stripe needs and why each setup step matters.",
                "exit_criteria": "Operator has the billing setup workspace, guidance, and next actions.",
            },
            {
                "id": "connect",
                "title": "Connect",
                "status": "complete"
                if check_map.get("api_key") and check_map.get("webhook_secret")
                else ("in_progress" if has_active_session else "not_started"),
                "goal": "Capture tenant-owned Stripe credentials and register a webhook endpoint.",
                "exit_criteria": "API key and webhook secret stored for the tenant.",
            },
            {
                "id": "configure",
                "title": "Configure",
                "status": "complete"
                if check_map.get("business_profile") and check_map.get("webhook_endpoint")
                else ("in_progress" if has_active_session or check_map.get("api_auth") else "not_started"),
                "goal": "Complete dashboard setup tasks like business profile, KYC, payouts, and webhook registration.",
                "exit_criteria": "Business profile submitted, webhook endpoint registered, and dashboard blockers known.",
            },
            {
                "id": "catalog",
                "title": "Catalog",
                "status": "complete"
                if check_map.get("catalog_sync")
                else ("in_progress" if check_map.get("api_auth") else "not_started"),
                "goal": "Review Mahoosuc templates and sync the right products and prices into the tenant Stripe account.",
                "exit_criteria": "Required offers exist in Stripe and at least one billable price is ready for testing.",
            },
            {
                "id": "validate",
                "title": "Validate",
                "status": "complete"
                if check_map.get("api_auth")
                and check_map.get("test_checkout_ready")
                and check_map.get("charges_enabled")
                else ("in_progress" if check_map.get("api_auth") else "not_started"),
                "goal": "Run readiness checks and prove the tenant can execute a billing flow safely.",
                "exit_criteria": "API auth succeeds, payouts/charges are enabled, and a test checkout path is available.",
            },
            {
                "id": "operate",
                "title": "Operate",
                "status": "complete"
                if connection.get("readiness_status") == "ready"
                else ("in_progress" if check_map.get("api_auth") else "not_started"),
                "goal": "Use the setup assistant as an ongoing copilot for catalog changes, webhook recovery, and operational health.",
                "exit_criteria": "Tenant billing admin is healthy and operators know which process to run for common changes.",
            },
        ]
        current_stage = next((stage["id"] for stage in stages if stage["status"] != "complete"), "operate")
        return {
            "current_stage": current_stage,
            "stages": stages,
            "operator_note": (
                "Human-regulated tasks stay in Stripe Dashboard. "
                "Mahoosuc tracks readiness, guidance, and catalog intent around those tasks."
            ),
        }

    def _process_playbooks(self, provider: str) -> list[dict[str, Any]]:
        if provider != "stripe":
            return []
        return [
            {
                "id": "new_tenant_onboarding",
                "title": "New Tenant Onboarding",
                "trigger": "A tenant is connecting Stripe for the first time.",
                "steps": [
                    "Start a guided setup session.",
                    "Capture API key and webhook secret in tenant storage.",
                    "Run health verification to surface KYC, payouts, and webhook blockers.",
                    "Review the starter catalog before sync.",
                ],
            },
            {
                "id": "catalog_change",
                "title": "Catalog Change",
                "trigger": "A tenant wants to add, remove, or reprice products.",
                "steps": [
                    "Refresh catalog diff.",
                    "Review recommended actions instead of editing active prices in place.",
                    "Sync selected offers.",
                    "Re-run health verification and confirm at least one test checkout path remains valid.",
                ],
            },
            {
                "id": "billing_recovery",
                "title": "Billing Recovery",
                "trigger": "Webhook delivery, payouts, or readiness checks regress after a dashboard change.",
                "steps": [
                    "Run health verification.",
                    "Open the failing capability card to identify the Stripe dashboard area involved.",
                    "Resume the guided setup flow or store updated credentials if secrets changed.",
                    "Re-run verification until readiness returns to ready.",
                ],
            },
        ]

    def _read_raw_credentials(self, provider: str, tenant_id: str) -> dict[str, str]:
        from instruments.custom.payment_account_setup.credential_store import PROVIDER_ENV_MAP

        env_map = PROVIDER_ENV_MAP.get(provider.lower(), {})
        raw: dict[str, str] = {}
        for logical, env_name in env_map.items():
            value = self.db.read_secret(tenant_id, provider, logical) or self.credential_store.read_credential(env_name)
            if value:
                raw[logical] = value
        return raw

    def _stripe_provider(self, api_key: str, webhook_secret: str | None, mock: bool = False):
        if mock:
            from instruments.custom.stripe_payments.providers.mock_provider import MockStripeProvider

            return MockStripeProvider()
        from instruments.custom.stripe_payments.providers.stripe_provider import StripeProvider

        return StripeProvider(api_key=api_key, webhook_secret=webhook_secret)

    def _fetch_stripe_remote_state(
        self,
        api_key: str,
        webhook_secret: str | None,
        mock: bool = False,
    ) -> tuple[bool, dict[str, Any], list[dict[str, Any]], str, str]:
        if mock:
            mode = "live" if str(api_key).startswith("sk_live_") else "test"
            mock_account = {
                "id": "acct_mock",
                "email": "mock@example.com",
                "details_submitted": True,
                "charges_enabled": True,
                "payouts_enabled": True,
                "requirements": {"currently_due": []},
            }
            webhook_url = os.environ.get("STRIPE_WEBHOOK_ENDPOINT_URL", "http://localhost:6274/api/stripe/webhook")
            mock_endpoints = [{"url": webhook_url, "status": "enabled"}]
            return True, mock_account, mock_endpoints, mode, ""
        client = self._stripe_provider(api_key=api_key, webhook_secret=webhook_secret, mock=False)
        try:
            account = client.get_account() if hasattr(client, "get_account") else {}
            endpoints = client.list_webhook_endpoints() if hasattr(client, "list_webhook_endpoints") else []
            mode = "live" if str(api_key).startswith("sk_live_") else "test"
            return True, account, endpoints, mode, ""
        except Exception as exc:
            return False, {}, [], "test", str(exc)

    def _load_steps(
        self,
        provider: str,
        session_id: str,
        email: str,
        webhook_endpoint_url: str,
    ) -> list[dict]:
        if provider == "stripe":
            from instruments.custom.payment_account_setup.step_definitions.stripe_steps import get_stripe_steps

            return get_stripe_steps(session_id, email, webhook_endpoint_url)
        if provider == "square":
            from instruments.custom.payment_account_setup.step_definitions.square_steps import get_square_steps

            return get_square_steps(session_id, email, webhook_endpoint_url)
        if provider == "paypal":
            from instruments.custom.payment_account_setup.step_definitions.paypal_steps import get_paypal_steps

            return get_paypal_steps(session_id, email, webhook_endpoint_url)
        raise ValueError(f"No step definitions for provider '{provider}'")
