# Security Review — 2026-04-05

## Scope

Pre-launch security review for Agent Jumbo GA. Covers authentication gates,
payment data handling, webhook verification, trust system, and known attack surfaces.

## Review Method

- Static analysis: Bandit, detect-secrets (pre-commit hooks, passing on all commits)
- Manual code review: auth middleware, payment providers, webhook handlers, trust gates
- Automated: `scripts/validate_360.sh` and `scripts/validate_release.sh` (both passing)

---

## Findings

### RESOLVED

| ID | Severity | Area | Finding | Resolution |
|----|----------|------|---------|------------|
| SEC-001 | High | stripe_provider.py | Self-referential class inheritance (`class StripePaymentProvider(StripePaymentProvider)`) silently worked but was a latent bug | Fixed: renamed to `class StripeProvider(PaymentProvider)` — 2026-04-05 |
| SEC-002 | Medium | Webhook handlers | Square and PayPal webhook endpoints had no signature verification | Fixed: `SquareWebhookHandler.verify_signature()` (HMAC-SHA256) and `PayPalWebhookHandler.verify_signature()` (PayPal API) — 2026-04-05 |
| SEC-003 | Low | credential_store.py | Key name strings flagged as potential secrets by detect-secrets | Fixed: `# pragma: allowlist secret` annotations on false-positive lines — 2026-04-05 |

### ACCEPTED FOR LAUNCH

| ID | Severity | Area | Finding | Acceptance rationale |
|----|----------|------|---------|----------------------|
| SEC-004 | Medium | PayPal webhooks | Sandbox fallback bypasses signature verification when `PAYPAL_CLIENT_ID` is unset | Acceptable: only active when `PAYPAL_CLIENT_ID` not set (i.e., not configured). Will not activate on production with credentials set. Log warning emitted. |
| SEC-005 | Low | Billing portal | `/billing/*` routes are auth-gated via Flask session but CSRF is not enforced on the blueprint | Low risk: portal actions are idempotent or reversible. CSRF protection should be added before handling high-value irreversible actions (e.g., delete account). |
| SEC-006 | Low | Browser setup | Browser automation instrument has no rate limit on `start_setup` | Acceptable: instrument is agent-only, not exposed to end users. |

### OPEN — MUST RESOLVE BEFORE LIVE PAYMENT KEYS

| ID | Severity | Area | Finding | Owner |
|----|----------|------|---------|-------|
| SEC-007 | High | All providers | Real payment API keys (`STRIPE_API_KEY`, `SQUARE_ACCESS_TOKEN`, `PAYPAL_CLIENT_SECRET`) are not yet configured | Engineering/Ops — required before live launch, not a code issue |
| SEC-008 | Medium | Stripe webhook | `STRIPE_WEBHOOK_SECRET` must be set and tested against real Stripe delivery | Engineering/Ops |

---

## Controls Verified

| Control | Status |
|---------|--------|
| Authentication required for all billing portal routes | ✅ Via existing `requires_auth` middleware |
| Payment credentials never logged | ✅ Credential values redacted in all log calls |
| detect-secrets baseline in pre-commit | ✅ Passing on all commits |
| Bandit static analysis | ✅ No high-severity findings |
| Webhook signature verification (Stripe) | ✅ HMAC-SHA256 via `construct_webhook_event` |
| Webhook signature verification (Square) | ✅ HMAC-SHA256 over raw body |
| Webhook signature verification (PayPal) | ✅ PayPal verify-webhook-signature API |
| Idempotency on Square writes | ✅ UUID idempotency key per write |
| SQLite WAL mode (prevents corruption) | ✅ All databases |
| Trust gate enforcement | ✅ Progressive trust system with stop-gates |

## Sign-off

- **Reviewer role:** Engineering/Security
- **Date:** 2026-04-05
- **Status:** Approved for launch — SEC-007 and SEC-008 must be completed with real keys before live payment processing
- **Next review:** Refresh after real payment keys are wired (2026-04-14 collection window)
