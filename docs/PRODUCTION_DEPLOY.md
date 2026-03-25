# Production Deployment Guide

Before treating any deployment as launch-ready, verify it against [Production GA Definition of Done](PRODUCTION_GA_DEFINITION_OF_DONE.md). This guide explains how to deploy; the GA definition determines whether the platform is actually ready to go live.

> Agent Jumbo — from development to production with confidence.

---

## Pre-Flight Checklist

- [ ] 1799+ tests pass (`python -m pytest tests/ -v --ignore=tests/integration -m "not e2e"`)
- [ ] `npm run build` succeeds in `web/`
- [ ] `.env` populated from `.env.example` with production values
- [ ] API keys rotated and verified
- [ ] `FLASK_SECRET_KEY` set (not auto-generated)
- [ ] Health check returns `{"ok": true}` — `curl http://localhost:50001/health`
- [ ] Backup created via backup API (`POST /backup_create`)

---

## Environment Variables

### Required (must set)

| Variable | Description |
|----------|-------------|
| `FLASK_SECRET_KEY` | Session signing key — **must** be explicitly set, not auto-generated |
| `AUTH_LOGIN` | Admin username |
| `AUTH_PASSWORD` | Admin password |
| `CHAT_MODEL_PROVIDER` | LLM provider (e.g., `openai`, `anthropic`, `google`) |
| `CHAT_MODEL_NAME` | Model name (e.g., `gpt-4o`, `claude-sonnet-4-20250514`) |
| `WEB_UI_HOST` | Bind address (use `0.0.0.0` for production) |
| `WEB_UI_PORT` | Port (default: `50001`) |

### Integration (set if using)

| Variable | Description |
|----------|-------------|
| `LINEAR_API_KEY` | Linear issue tracker integration |
| `MOTION_API_KEY` | Motion calendar integration |
| `NOTION_API_KEY` | Notion workspace integration |
| `TELEGRAM_BOT_TOKEN` | Telegram messaging gateway |
| `TELEGRAM_WEBHOOK_SECRET` | Webhook verification secret |
| `GMAIL_APP_PASSWORD` | Gmail SMTP integration |
| `GMAIL_FROM_EMAIL` | Sender email address |

### Observability (recommended)

| Variable | Description |
|----------|-------------|
| `LANGSMITH_API_KEY` | LangSmith tracing |
| `LANGFUSE_PUBLIC_KEY` | Langfuse observability (public key) |
| `LANGFUSE_SECRET_KEY` | Langfuse observability (secret key) |

### Reference

Full list of 272+ documented variables: `.env.example`

---

## Secret Rotation Schedule

| Secret | Frequency | Method |
|--------|-----------|--------|
| `AUTH_PASSWORD` | 90 days | Update `.env`, restart |
| LLM API keys | Per provider policy | Update `.env`, restart |
| `FLASK_SECRET_KEY` | 90 days | Update `.env`, restart (invalidates sessions) |
| `LINEAR_API_KEY` / `MOTION_API_KEY` / `NOTION_API_KEY` | 90 days | Rotate in provider dashboard, update `.env` |
| `TELEGRAM_WEBHOOK_SECRET` | 90 days | Regenerate, update `.env` and Telegram config |

---

## Deployment Methods

### Docker (recommended)

```bash
# Build
docker build -t agent-jumbo:latest .

# Run
docker run -d \
  --name agent-jumbo \
  --env-file .env \
  -p 50001:50001 \
  -v $(pwd)/memory:/app/memory \
  -v $(pwd)/knowledge:/app/knowledge \
  agent-jumbo:latest

# Verify
curl http://localhost:50001/health | python -m json.tool
```

### Manual (bare metal)

```bash
# Prerequisites: Python 3.11+, Node.js 18+

# 1. Install dependencies
pip install -r requirements.txt
cd web && npm ci && npm run build && cd ..

# 2. Configure environment
cp .env.example .env
# Edit .env with production values

# 3. Start
python run_ui.py

# 4. Verify
curl http://localhost:50001/health
```

### Vercel (frontend only)

Deploy the `web/` directory to Vercel for the Next.js frontend. The Flask backend must be hosted separately. Set the `NEXT_PUBLIC_API_URL` environment variable in Vercel to point to the backend.

---

## Monitoring

### Health Endpoint

Poll `GET /health` every 30 seconds. The response includes subsystem checks:

```json
{
  "ok": true,
  "status": "healthy",
  "checks": {
    "git": { "ok": true, "info": { "branch": "main", "commit": "abc123" } },
    "disk": { "ok": true, "free_gb": 42.5 },
    "memory": { "ok": true, "rss_mb": 256.3 },
    "uptime_seconds": 3600.0,
    "runtime_metrics": { ... }
  }
}
```

### Alert Conditions

| Condition | Severity | Action |
|-----------|----------|--------|
| `ok: false` or non-200 response | Critical | Page on-call |
| `checks.disk.free_gb < 2.0` | Warning | Investigate disk usage |
| `checks.disk.free_gb < 1.0` | Critical | Free space immediately |
| Health endpoint unreachable | Critical | Check process, restart if needed |

### Structured Logging

Configure JSON output for log aggregators:

```bash
export LOG_FORMAT=json
export LOG_LEVEL=INFO
```

---

## Backup & Recovery

### Create Backup

```bash
curl -X POST http://localhost:50001/backup_create \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <token>"
```

### Restore Backup

```bash
curl -X POST http://localhost:50001/backup_restore \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <token>" \
  -d '{"id": "<backup-id>"}'
```

### Recommended Schedule

- **Daily:** Automated backup via scheduler API
- **Before deployments:** Manual backup
- **Retention:** Keep 7 daily, 4 weekly, 3 monthly backups

---

## Deployment Tiers

| Capability | Free | Pro | Enterprise |
|------------|------|-----|------------|
| Max sessions | 2 | 25 | Custom |
| Persona systems | No | Yes | Yes |
| Memory recall | No | Yes | Yes |
| LLM router | No | Yes | Yes |
| Multi-channel messaging | No | Yes | Yes |
| Priority support | No | No | Yes |

---

## Troubleshooting

### Common Issues

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| 502 Bad Gateway | Backend not running | Check `python run_ui.py` process |
| CSRF token errors | Missing or stale token | Clear cookies, reload |
| Health returns `degraded` | Disk space low | Free disk space, check `checks.disk.free_gb` |
| Settings not persisting | File permissions | Check write permissions on `settings/` directory |

### Log Locations

- **Application logs:** stdout/stderr (redirect to file with `2>&1 | tee app.log`)
- **Structured logs:** `logs/` directory (when `LOG_FORMAT=json`)
- **Backup logs:** Available via backup API response
