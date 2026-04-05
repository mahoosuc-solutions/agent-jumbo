---
title: Self-Serve GA Onboarding
description: Canonical onboarding path for a new self-serve customer setting up Agent Jumbo for production use.
date: 2026-03-24
---

# Self-Serve GA Onboarding

This is the canonical onboarding path for a new self-serve customer in the current production GA plan. If another setup document conflicts with this one, this document wins for launch.

## Intended Outcome

A new customer should be able to:

1. Understand what is being purchased
2. Prepare the required environment and credentials
3. Deploy the platform
4. Verify that the platform is healthy
5. Complete first login and first chat
6. Understand where to get help if setup fails

## Before You Start

You need all of the following before beginning:

- A host environment that matches the deployment guide
- Python **3.11+** for backend/runtime tooling
- Node.js **18+** for the `web/` application
- Docker, if using the Docker deployment path
- Access to the repository and deployment target
- A payment or sales-confirmed activation path aligned with published pricing

## Required Configuration

At minimum, configure these variables before go-live use:

| Variable | Why it matters |
|---|---|
| `FLASK_SECRET_KEY` | Required for session signing |
| `AUTH_LOGIN` | Initial admin login |
| `AUTH_PASSWORD` | Initial admin password |
| `CHAT_MODEL_PROVIDER` | Required for chat routing |
| `CHAT_MODEL_NAME` | Required for chat routing |
| `WEB_UI_HOST` | Required for backend binding |
| `WEB_UI_PORT` | Required for backend binding |
| `NEXT_PUBLIC_API_URL` | Required for the web frontend |
| `NEXT_PUBLIC_URL` | Required for public frontend behavior |

Optional integrations must be treated as optional during onboarding unless they are part of the purchased plan.

## Step 1: Confirm Launch Scope

Before setup, confirm the customer is buying the current GA scope:

- core app startup and auth
- chat create, async message flow, and poll lifecycle
- trust-gated execution
- dashboard navigation and current dashboard surfaces
- public product page and platform status API
- backup, graceful shutdown, and restore workflow
- Stripe-backed commercial path

Do not promise features still treated as `beta` or `internal` in [GA Launch Inventory](GA_LAUNCH_INVENTORY.md).

## Step 2: Prepare Backend

Follow [Production Deployment Guide](PRODUCTION_DEPLOY.md) for the deployment method.

Minimum backend acceptance checks:

```bash
curl http://localhost:50001/health
curl http://localhost:50001/chat_readiness
```

Expected result:

- `/health` returns success
- `/chat_readiness` reports ready

If either check fails, stop onboarding and fix infrastructure before continuing.

## Step 3: Prepare Frontend

From `web/`:

```bash
npm install
npm run type-check
npm run build
```

Deploy the frontend using the configured delivery path. The frontend must point at the correct backend via `NEXT_PUBLIC_API_URL`.

## Step 4: Validate Core Runtime

Run the release evidence checks that correspond to the current GA package:

```bash
./scripts/validate_release.sh
./scripts/validate_360.sh
```

If using a Docker-based target environment, also run:

```bash
./scripts/validate_deployment.sh
```

Store the resulting logs under `artifacts/validation/` for the launch packet.

## Step 5: First Login and First Chat

After deployment:

1. Open the public or internal URL
2. Log in with the configured admin credentials
3. Create a new chat
4. Send a smoke message
5. Confirm the async message flow settles normally
6. Confirm dashboard navigation works
7. Confirm trust-level UX is visible and understandable

Minimum manual smoke evidence:

- product page accessible
- login succeeds
- new chat is created and selected
- one chat request completes
- dashboards load
- backup path is visible and documented

## Step 6: Backup and Restore

Before calling onboarding complete:

1. Create a backup
2. Confirm backup artifact exists
3. Rehearse restore on a safe environment or according to the launch runbook

If backup or restore fails, do not mark the customer environment as production ready.

## Step 7: Support and Escalation

The customer must know:

- where to report setup failures
- where payment problems are handled
- where incident updates will be communicated
- how data deletion and account closure requests are handled

Link the final production versions of privacy, terms, retention, and deletion docs before GA.
Use [Customer Support](CUSTOMER_SUPPORT.md) as the canonical support, incident, billing, and remediation path.

## Onboarding Completion Checklist

- [ ] Backend deployed
- [ ] Frontend deployed
- [ ] Required environment variables configured
- [ ] `/health` green
- [ ] `/chat_readiness` green
- [ ] `validate_release.sh` green
- [ ] `validate_360.sh` green
- [ ] `validate_deployment.sh` green if applicable
- [ ] First login complete
- [ ] First chat smoke complete
- [ ] Dashboard smoke complete
- [ ] Backup and restore checked
- [ ] Support, privacy, and terms links provided
- [ ] Customer support path provided from the canonical support document

## Troubleshooting: Common Failure States

### Missing or invalid API keys

If `CHAT_MODEL_PROVIDER` or `CHAT_MODEL_NAME` is unset or invalid:

- `/chat_readiness` will report `not_ready` with a message identifying the missing key
- Chat creation will succeed but message delivery will fail
- **Fix:** Set the correct API key and restart the backend

If `FLASK_SECRET_KEY` is unset:

- The backend will start but sessions will not persist across restarts
- **Fix:** Set a strong, random secret key and restart

### Invalid credentials

If `AUTH_LOGIN` or `AUTH_PASSWORD` is incorrect or unset:

- Login will fail with a generic error message (no credential leak)
- **Fix:** Set the correct credentials in the environment and restart

### Backend unreachable

If the frontend cannot reach `NEXT_PUBLIC_API_URL`:

- Health checks will fail
- Chat and dashboard features will show connection errors
- **Fix:** Verify the backend is running, the URL is correct, and there are no firewall/proxy issues

### Stripe / payment failures

If `STRIPE_API_KEY` is invalid or unset:

- Payment-related tools will return errors but will not crash the platform
- The billing portal will render but cannot process payments
- **Fix:** Configure a valid Stripe API key (test or live) and set `STRIPE_WEBHOOK_SECRET`

### Degraded status API

If the backend is down but the frontend is deployed:

- The platform status API will return a connection error
- The product page will fall back to static-only display
- **Fix:** Restore the backend and verify `/health` returns green

## Resolved Known Gaps

The following items from the 2026-03-24 review are now resolved:

- ~~customer-facing privacy, terms, retention, and deletion publication package~~ — Published at `/documentation/PRIVACY_POLICY`, `/documentation/TERMS_OF_USE`, `/documentation/DATA_RETENTION_POLICY`, `/documentation/DATA_DELETION_POLICY` (verified 2026-04-05)
- ~~final support and escalation contact path~~ — Published at `/documentation/CUSTOMER_SUPPORT` and linked from pricing page (verified 2026-04-05)
- ~~fresh manual smoke evidence for March platform features~~ — Manual smoke record captured 2026-04-05 covering health, scheduler, dashboards, chat, and trust UX
- ~~Python 3.11+ release environment baseline~~ — Confirmed in `validate_release.sh` and `pyproject.toml`
