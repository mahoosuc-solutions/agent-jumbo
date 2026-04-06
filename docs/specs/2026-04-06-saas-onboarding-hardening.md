# SaaS Onboarding & Security Hardening Plan

**Date:** 2026-04-06
**Authors:** SaaS Product Architect + Security Architect (AI-assisted)
**Status:** Proposed — requires review

---

## Executive Summary

The MOS↔Agent Jumbo integration is live and working. This plan addresses the gaps between "demo-ready" and "production SaaS" — focusing on API-driven user provisioning, security hardening, durable metering, and guided onboarding.

**Prioritization:** Security hardening and revenue enablement first, then growth features, then technical debt.

---

## Phase 1: Security Hardening (Week 1-2) — Production Trust

### 1A. Redis-Backed Token Stores

**Problem:** Relay tokens and OAuth state are in-memory Maps — lost on restart.
**Fix:** Move to Redis with TTL keys. Use `GETDEL` for atomic single-use relay exchange.

- `mos:oauth_state:{hex}` — 600s TTL
- `mos:relay:{hex}` — 30s TTL with JSON payload
- **File:** `aios-backend/src/services/oauthService.ts`

### 1B. Service-to-Service HMAC Auth

**Problem:** `x-internal-service` header has zero authentication — anything on the Docker network can impersonate system.
**Fix:** HMAC-SHA256 signature with shared secret from Vault, timestamp + path + service name.

- **Files:** `platform.routes.ts`, `mos_auth.py`, `usage_enforcement.py`

### 1C. Fail-Closed Entitlement Checks

**Problem:** `mos_auth.check_entitlement()` returns True on network error (fail-open).
**Fix:** Default to fail-closed. Add circuit breaker: stale-while-revalidate after 5 consecutive failures.

- **File:** `agent-jumbo/python/helpers/mos_auth.py`
- **Config:** `ENTITLEMENT_FAIL_MODE=closed|open`

### 1D. Per-Endpoint Rate Limiting with Redis

**Problem:** Flask-Limiter uses `memory://` storage, rate limits reset on restart.
**Fix:** Switch to Redis backend. Add per-endpoint limits:

- `/auth/relay`: 10/min
- Chat operations: 30/min per org
- `/login` POST: 5/min
- **File:** `agent-jumbo/run_ui.py`

### 1E. Relay Security Hardening

**Fix:** Regenerate Flask session ID after relay exchange (prevent session fixation). Add nonce parameter. Add `Referrer-Policy: no-referrer` on redirect.

- **File:** `agent-jumbo/run_ui.py` relay_handler

---

## Phase 2: Durable Metering & Trial Management (Week 3-4) — Revenue

### 2A. Redis-Backed Usage Metering

**Problem:** In-memory counters reset on restart.
**Fix:** Redis `INCRBY` on `usage:{org_id}:{YYYY-MM}:operations` with 45-day TTL. Daily snapshots to `usage_snapshots` table.

- **File:** `agent-jumbo/python/helpers/usage_enforcement.py`
- **New migration:** `usage_snapshots` table

### 2B. Automated Trial Expiry

**Problem:** `trial_ends_at` is stored but never enforced.
**Fix:** Hourly cron job checks expired trials → transitions to `disabled`. 3-day grace period with `trial_expiring` intermediate state. Email notifications.

- **File:** `aios-backend/src/services/platformProductsService.ts`
- **New endpoint:** `GET /api/portal/trial-status`

### 2C. Webhook→Entitlement Bridge (Complete)

**Problem:** The webhook handler writes to `billing_subscriptions` but doesn't always update `platform_product_entitlements` correctly.
**Fix:** After subscription create/update/delete, call MOS entitlement API with HMAC auth from Phase 1B. Handle payment_failed → disable after 7 days past_due.

- **File:** `services/billing/src/services/WebhookService.ts`

---

## Phase 3: API-Driven User Provisioning (Week 5-6) — Growth

### 3A. Public Registration API

```
POST /api/auth/register
  { email, password, full_name, product_key?, organization_name? }
  → { user, organizations, accessToken, refreshToken, trial_status }
```

Wire through `provisionSelfServeUser()` so registration creates org + membership + trial in one call.

### 3B. Team Invitation API

```
POST /api/org/invite          — invite by email + role
GET  /api/org/invitations     — list pending
POST /api/auth/accept-invite  — accept with token
DELETE /api/org/invite/:id    — cancel
```

**New table:** `organization_invitations` with 7-day token expiry.

### 3C. Organization Management API

```
GET    /api/org              — org details
PUT    /api/org              — update org
GET    /api/org/members      — list members
PUT    /api/org/members/:id  — change role
DELETE /api/org/members/:id  — remove member
```

### 3D. Subscription Management API

```
POST /api/portal/upgrade     — checkout for higher tier
POST /api/portal/downgrade   — schedule at period end
GET  /api/portal/usage       — current vs limits
GET  /api/portal/invoices    — Stripe invoice history
```

---

## Phase 4: Guided Onboarding UX (Week 7-8) — Retention

### 4A. Onboarding Wizard API

```
GET  /api/onboarding/status  — current stage + completed steps
POST /api/onboarding/step    — mark step complete
POST /api/onboarding/skip    — skip optional step
```

Stages: `signup → product_selected → trial_started → first_use → team_invited → complete`

### 4B. Product Selection During Signup

Show product picker between registration and dashboard. Pass `productKey` through existing `provisionSelfServeUser()`.

### 4C. Multi-Tenant Data Isolation

Add `organization_id` to all Agent Jumbo data tables. Row-level scoping middleware injects org from session. Enforces the `data_mode: isolated` declaration.

---

## Phase 5: Auth Unification (Week 9-10) — Technical Debt

### 5A. Asymmetric JWT Signing (RS256)

Move from shared HS256 secret to RS256 key pair. MOS signs with private key, products verify with public key via JWKS endpoint `/.well-known/jwks.json`. Enables key rotation without downtime.

### 5B. Session Hardening

- Max 3 concurrent sessions per user (Redis tracking)
- Session ID regeneration after relay
- IP + user-agent binding
- Redis-backed Flask sessions (replace filesystem)

---

## Priority Matrix

| Phase | Impact | Risk | Effort | Start |
|-------|--------|------|--------|-------|
| 1: Security | Medium biz, **Critical risk** | Blocks prod trust | 2 wk | Immediately |
| 2: Metering | **High** (revenue) | High | 2 wk | Parallel w/ Phase 1 |
| 3: Provisioning | **High** (growth) | Medium | 2 wk | After Phase 1 |
| 4: Onboarding | Medium (retention) | Low | 2 wk | After Phase 3 |
| 5: Auth Unification | Low (tech debt) | Medium | 2 wk | After Phase 4 |

**Total:** 10 weeks to fully production-hardened SaaS, parallelizable to ~7 weeks.

---

## Verification Plan

After each phase:

1. **Security scan** — run bandit (Python) + npm audit + OWASP ZAP against public endpoints
2. **Integration test** — full signup → trial → usage → upgrade → cancel flow via API
3. **Load test** — 100 concurrent users through the relay flow + chat operations
4. **Penetration test** — after Phase 1, specifically test token replay, CSRF, IDOR
