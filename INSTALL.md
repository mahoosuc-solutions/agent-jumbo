# Installation Guide

> Self-serve installation for Agent Jumbo. For production GA deployment details see [docs/PRODUCTION_DEPLOY.md](docs/PRODUCTION_DEPLOY.md).

## Requirements

- Docker Desktop 4.x+ (Windows/Mac) or Docker Engine 24+ (Linux)
- 8 GB RAM minimum, 16 GB recommended
- 20 GB free disk space
- LLM API key (Anthropic, OpenAI, Google, or Ollama local)

## Quick Start (Docker — recommended)

```bash
# 1. Clone
git clone https://github.com/mahoosuc-solutions/agent-jumbo.git
cd agent-jumbo

# 2. Configure
cp .env.example .env
# Edit .env: set CHAT_MODEL_PROVIDER, CHAT_MODEL_NAME, API keys, FLASK_SECRET_KEY

# 3. Build and start
./scripts/docker-deploy.sh deploy

# 4. Open
open http://localhost:6274
```

Health check: `curl http://localhost:6274/health` → `{"ok": true}`

## Environment Variables

Copy `.env.example` to `.env` and set at minimum:

| Variable | Description | Example |
|----------|-------------|---------|
| `FLASK_SECRET_KEY` | Session signing key (32+ chars) | `openssl rand -hex 32` |
| `CHAT_MODEL_PROVIDER` | LLM provider | `anthropic` |
| `CHAT_MODEL_NAME` | Model name | `claude-sonnet-4-6` |
| `AUTH_LOGIN` | Admin username | `admin` |
| `AUTH_PASSWORD` | Admin password | _(strong password)_ |

Full variable reference: [`.env.example`](.env.example) (272+ variables documented).

## Production Deployment (Linux server)

```bash
# Build production image
docker compose -f docker-compose.prod.yml build

# Start with restart policy
docker compose -f docker-compose.prod.yml up -d

# Check health
docker ps --filter name=agent-jumbo-production
```

Port mapping: host `6274` → container `80`.

## Windows (auto-start service)

Scripts in `C:\Users\<you>\agent-jumbo\`:

```powershell
.\Start-AgentJumbo.ps1    # Start
.\Stop-AgentJumbo.ps1     # Stop
.\Status-AgentJumbo.ps1   # Status
.\Logs-AgentJumbo.ps1     # Live logs
```

Register auto-start on login (run once as Administrator):

```powershell
.\Register-AutoStart.ps1
```

## Local Development (Python)

```bash
pip install uv
uv sync
cp .env.example .env
# Edit .env
python run_ui.py
```

Runs on `http://localhost:50080`.

## Web Frontend (Next.js)

```bash
cd web
cp .env.example .env.local
npm install
npm run dev   # dev server at http://localhost:3000
npm run build # production build
```

## Validation

After installation, verify the platform is healthy:

```bash
BASE_URL=http://localhost:6274 bash scripts/validate_360.sh quick
```

Expected: `Summary: pass=10 fail=0`

## Upgrading

```bash
git pull
CONTAINER=agent-jumbo-production BASE_URL=http://localhost:6274 ./scripts/docker-deploy.sh deploy
```

The deploy script builds a new image, replaces the running container, and waits for the health check to pass before reporting success.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Container exits immediately | Check `docker logs agent-jumbo-production` — missing required env var |
| Health check returns `ok: false` | Check disk space (`df -h`) and memory |
| LLM calls fail | Verify API key in `.env` and model name is correct for provider |
| Auth loop | Ensure `AUTH_LOGIN` and `AUTH_PASSWORD` are set; clear browser cookies |

## Support

File issues at [mahoosuc-solutions/agent-jumbo](https://github.com/mahoosuc-solutions/agent-jumbo/issues).
