# Agent Jumbo — Hetzner Deployment & MOS Integration Design

> **Date:** 2026-04-06
> **Status:** Approved
> **Author:** Claude + Aaron
> **Cost:** ~$30/mo incremental (CPX42 only)

## Executive Summary

Deploy agent-jumbo to a dedicated Hetzner CPX42 server (`168.119.49.252`), integrated with the existing MOS production platform (`46.224.170.197`) via WireGuard tunnel and AgentMesh Redis bridge. Access is VPN-gated — no public exposure. Build artifacts flow through the canonical build server (`49.13.125.252`) per MOS deployment runbook rules.

## Architecture

```
 Your devices (phone/laptop)
         |
         | WireGuard
         v
+------------------------+
|  agent-jumbo (CPX42)   |
|  168.119.49.252        |
|  WG: 10.0.0.3          |
|                        |
|  Caddy (TLS, bind WG)  |
|  agentjumbo.mahoosuc.ai|
|  :443 -> container:6274|
|                        |
|  WG peers:             |
|  10.0.0.1 mos-prod     |
|  10.0.0.2 laptop/WSL   |
|  10.0.0.4 phone        |
+----------+-------------+
           | WireGuard
           v
+------------------------+
|  mos-prod              |
|  46.224.170.197        |
|  WG: 10.0.0.1          |
|  Redis :6379           |
|  AIOS API :3013        |
|  Vault :8200 (local)   |
+------------------------+
```

### Key Decisions

- Agent-jumbo runs on its own server, not on mos-prod (isolation, independent scaling)
- WireGuard tunnel between CPX42 and mos-prod for all Redis/API traffic — never over public internet
- Caddy on CPX42 handles TLS for `agentjumbo.mahoosuc.ai`, bound to WG interface only
- Firewall blocks public access to 443/80 — only WG peers can reach the UI
- DNS challenge (Hetzner DNS API) for Let's Encrypt — no public port 80 needed
- Split DNS via WG config — clients resolve `agentjumbo.mahoosuc.ai` to `10.0.0.3`

## Infrastructure

### Servers

| Server | IP | Spec | Role |
|--------|-----|------|------|
| `agent-jumbo` (CPX42) | `168.119.49.252` | x86 8c/16GB/320GB, fsn1 | Deploy host |
| `mos-prod` (CCX23) | `46.224.170.197` | 4c/16GB/160GB | MOS platform, Redis, Vault |
| Build server | `49.13.125.252` | Existing | Build-only lane |

### WireGuard Mesh

| Peer | WG IP | Role |
|------|-------|------|
| mos-prod | `10.0.0.1` | MOS platform (existing) |
| Laptop/WSL | `10.0.0.2` | Dev access (existing peer def) |
| CPX42 (agent-jumbo) | `10.0.0.3` | Deploy host (new) |
| Phone | `10.0.0.4` | Mobile access (new) |

CPX42 acts as WG hub — all peers connect to it. ListenPort: 51820.

### Firewall (CPX42)

| Rule | Port | Protocol | Source | Description |
|------|------|----------|--------|-------------|
| Allow | 51820 | UDP | `0.0.0.0/0` | WireGuard handshake |
| Allow | 22 | TCP | Known IPs only | SSH |
| Allow | 443 | TCP | `10.0.0.0/24` | HTTPS via WG only |
| Allow | 80 | TCP | `10.0.0.0/24` | HTTP redirect via WG only |
| Allow | ICMP | — | `10.0.0.0/24` | Ping |
| Deny | * | * | `0.0.0.0/0` | Default deny |

### DNS

- `agentjumbo.mahoosuc.ai` A record -> `168.119.49.252` (public, for SSH/WG endpoint)
- WG clients override resolution to `10.0.0.3` via split DNS config

## Build & Deploy Pipeline

### Non-Negotiable Rules (from MOS runbook)

- Build only on the build server (`49.13.125.252`)
- Deploy only on the deploy host (`168.119.49.252`)
- GitHub Actions is CI-only — must NOT deploy to Hetzner
- Vault is the secrets control plane — AppRole auth on deploy host
- No secrets in build artifacts, no `.env` files in git
- Build server must not hold Vault tokens, AppRole secret IDs, or production env files

### Build Server Contract

Host: `49.13.125.252`

Build server responsibilities:

- Build from a pinned commit SHA
- Produce immutable Docker image + manifest + checksums
- Run bridge-contract tests
- Smoke validation: `/health`, `/health_agentmesh`, `POST /agentmesh_validate`
- Export evidence bundle (artifact ID, SHA, test summary)

Build server must NOT:

- Store Vault root tokens or long-lived AppRole secret IDs
- Store customer secret material
- Own Hetzner deployment or run host-side deploy commands

### Deployment Handoff

```
1. Build server creates artifact and evidence
2. Deploy host retrieves approved artifact (docker pull or scp)
3. Deploy host resolves Vault-backed runtime config via AppRole
4. Deploy host runs pre-deploy hooks
5. Deploy host starts agent-jumbo (docker compose up)
6. Deploy host runs post-deploy verification
7. On failure: auto-rollback + Telegram alert
```

## Cloud-Portable Docker Compose

New file: `docker-compose.cloud.yml`

### Removed (local-only assumptions)

- `/mnt/wdblack:/mnt/wdblack:rw` — no local drive on VPS
- `${HOME}/.ssh:/root/.ssh:ro` — not needed on server
- `${HOME}/.config:/root/.config:rw` — not needed on server
- `AGENT_JUMBO_SCHEDULER_SEED_PATH` pointing to local path
- `pull_policy: never` — changed to pull from build server
- WBM MCP sidecar containers — excluded, stays local

### Kept

- Named volumes: `agent_jumbo_data`, `agent_jumbo_logs`, `agent_jumbo_venv`
- Health check config (30s interval, 90s start period)
- Resource limits: 4 CPU / 8GB (half the box)
- `host.docker.internal` extra host (for WG-routed mos-prod access)

## Pre-Deploy Hook Pipeline

### Gate Tiers

| Tier | Behavior |
|------|----------|
| **Hard block** | Abort deploy, no container started |
| **Soft block** | Auto-rollback to previous image |
| **Advisory** | Warn via Telegram, continue |

### Pipeline Stages

#### PRE-DEPLOY (before docker compose up)

**Stage 1: Artifact Validation** (Hard block)

- Verify artifact checksum matches build server manifest
- Verify pinned commit SHA matches expected
- Verify evidence bundle present (test summary, smoke results)

**Stage 2: Env / Secrets Validation** (Hard block)

- Vault reachable (AppRole auth succeeds)
- All required env vars resolved (no empty critical vars)
- `AGENTMESH_REDIS_URL` resolves and Redis responds to PING
- Telegram bot token valid (`getMe` API check)

**Stage 3: Network Pre-flight** (Hard block for WG/Redis, Advisory for DNS/AIOS)

- WireGuard tunnel to mos-prod alive (`ping 10.0.0.1`)
- Redis on mos-prod reachable (`10.0.0.1:6379`)
- AIOS API reachable (`10.0.0.1:3013/health`) — advisory
- DNS for `agentjumbo.mahoosuc.ai` resolves — advisory

**Stage 4: Image Checks** (Hard block)

- `check_instrument_packages.sh`
- `check_build_context.sh`
- `check_image_imports.sh`

#### POST-DEPLOY (within 90s startup window)

**Stage 5: Health Verification** (Soft block)

- `GET /health` returns ok (retry 12x @ 10s)
- `GET /health_agentmesh` shows `connected=true`
- `POST /agentmesh_validate` returns ok
- AgentMesh stream consumer presence confirmed

**Stage 6: Rollback Gate** (Soft block)

- If any post-deploy check fails: stop new container
- Restart previous image (keep last 2 tagged)
- Emit alert to Telegram

### Implementation

Single script: `scripts/cloud-deploy.sh`

- Extends existing `docker-deploy.sh` hook pattern
- Reuses `run_check()` function
- Adds cloud-specific gates as new check scripts in `scripts/checks/`

## Caddy Configuration

```caddy
agentjumbo.mahoosuc.ai {
    bind 10.0.0.3

    tls {
        dns hetzner {env.HETZNER_API_KEY}
    }

    reverse_proxy localhost:6274 {
        health_uri /health
        health_interval 30s
        health_timeout 5s
    }

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Frame-Options SAMEORIGIN
        X-Content-Type-Options nosniff
        X-XSS-Protection "1; mode=block"
        Referrer-Policy strict-origin-when-cross-origin
    }

    log {
        output file /var/log/caddy/agentjumbo-access.log
    }
}
```

- Bound to WG interface (`10.0.0.3`) only — not publicly reachable
- DNS challenge via Hetzner DNS API plugin — no public port 80 needed
- Auto-renewing Let's Encrypt certificates

## Runtime Configuration

All secrets resolved from Vault via AppRole at deploy time. Not baked into images.

### Required Env Vars

| Category | Vars | Source |
|----------|------|--------|
| AgentMesh | `AGENTMESH_REDIS_URL=redis://10.0.0.1:6379` | Vault |
| AIOS | `AIOS_BASE_URL=http://10.0.0.1:3013` | Vault |
| LLM | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` | Vault |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_ALERT_CHAT_ID` | Vault |
| Auth | `AUTH_LOGIN`, `AUTH_PASSWORD`, `FLASK_SECRET_KEY` | Vault |
| Integrations | `LINEAR_API_KEY`, `MOTION_API_KEY`, `NOTION_API_KEY` | Vault |
| Stripe | `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET` | Vault |
| Runtime | `AGENT_JUMBO_RUN_MODE=production`, `DEPLOYMENT_MODE=cloud` | Static |
| Gmail | `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET` | Vault |

### Disabled on Cloud

- `AGENT_JUMBO_LAPTOP_MODE=false`
- `CODE_EXEC_SSH_ENABLED=false`
- `OLLAMA_BASE_URL` — no local Ollama (API providers only)
- SearXNG — optional, enable later if needed

### Telegram

- Bot uses polling (not webhooks) — no inbound port needed
- Telegram orchestrator runs inside the Flask container
- Same bot token and chat IDs as local — works from any host
- `TELEGRAM_ALERT_CHAT_ID` used by rollback gate for deploy failure alerts

## Rollback Strategy

### Image Tagging

```
agent-jumbo:current    <- running now
agent-jumbo:previous   <- last known good
agent-jumbo:<sha>      <- immutable, from build server
```

### Rollback Flow

1. Post-deploy health checks fail
2. `docker compose down` the new container
3. Retag `agent-jumbo:previous` -> `agent-jumbo:current`
4. `docker compose up -d`
5. Verify health
6. Send Telegram alert with failure details and rolled-back SHA

## Monitoring

| Check | Method | Frequency |
|-------|--------|-----------|
| Container health | Docker healthcheck (`/health`) | Every 30s |
| AgentMesh bridge | `GET /health_agentmesh` | Every 60s via cron |
| WG tunnel alive | `ping -c 1 10.0.0.1` | Every 60s via cron |
| Disk usage | `df` threshold check | Every 5min via cron |
| Failed health -> alert | Cron script -> Telegram | On failure |

No external monitoring service — deploy host self-monitors and alerts via Telegram.

## GitHub Actions (CI-only)

Existing CI workflows remain unchanged:

- `ci.yml` — lint, tests, security, type-check, e2e
- `web-deploy.yml` — Vercel web UI deployment

No new GitHub Actions workflow for Hetzner deploy. Build and deploy are handled by the build server and deploy host respectively.

## Cost

| Item | Cost/mo |
|------|---------|
| CPX42 (8c/16GB, fsn1) | $29.99 |
| mos-prod (shared, existing) | $0 |
| Build server (shared, existing) | $0 |
| DNS, TLS, Telegram, bandwidth | $0 |
| **Total incremental** | **~$30/mo** |
