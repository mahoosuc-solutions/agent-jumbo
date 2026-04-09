# Agent Mahoo — Production Docker Deployment

Production Docker setup with baked image, persistent volumes, and local drive access.

## Architecture

**Image Strategy:**

- Code baked into image at build time (immutable)
- Python dependencies cached in named volume
- Data persists across container restarts

**Volume Mounts:**

- `agent_mahoo_data` → `/aj/data` (runtime data: SQLite DBs, uploads)
- `agent_mahoo_logs` → `/aj/logs` (application logs)
- `agent_mahoo_venv` → `/opt/venv-a0` (Python virtual environment cache)
- `/mnt/wdblack` → `/mnt/wdblack` (full WD Black drive access)
- `~/.ssh` → `/root/.ssh` (SSH keys, read-only)
- `~/.config` → `/root/.config` (user configs)

**Network:**

- External port: `6274` (Agent Mahoo default)
- Internal port: `80`
- Health check: `GET /health` every 30s

**Resources:**

- Limit: 4 CPUs, 8GB RAM
- Reservation: 1 CPU, 2GB RAM

---

## Quick Start

### Full Deployment (Build + Start)

```bash
./scripts/docker-deploy.sh deploy
```

This builds the image and starts the container. Agent Mahoo will be available at `http://localhost:6274`.

### Individual Commands

```bash
# Build the production image (no cache)
./scripts/docker-deploy.sh build

# Start the container (creates volumes if needed)
./scripts/docker-deploy.sh start

# Stop the container
./scripts/docker-deploy.sh stop

# Restart the container
./scripts/docker-deploy.sh restart

# Follow logs
./scripts/docker-deploy.sh logs

# Show status (container, volumes, health)
./scripts/docker-deploy.sh status
```

---

## Pre-Deployment Checklist

1. **Environment File**: Ensure `.env` exists with required keys:

   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

2. **Mount Points**: Verify required directories exist:

   ```bash
   ls -ld /mnt/wdblack ~/.ssh ~/.config
   ```

3. **Docker Volumes**: Script auto-creates if missing, but verify existing ones:

   ```bash
   docker volume ls | grep agent_mahoo
   ```

4. **Base Image**: Ensure `agent0ai/agent-zero-base:latest` is available:

   ```bash
   docker pull agent0ai/agent-zero-base:latest
   ```

---

## Configuration

### Environment Variables

Key `.env` settings for production:

```bash
# Agent Mahoo Mode
AGENT_MAHOO_RUN_MODE=production
AGENT_MAHOO_LAPTOP_MODE=false

# Mahoosuc OS Integration (optional)
AGENTMESH_REDIS_URL=redis://your-redis-host:6379
AIOS_BASE_URL=https://your-mahoosuc-os-instance.com

# LLM Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Local Ollama (if using)
OLLAMA_BASE_URL=http://host.docker.internal:11434

# File Ownership (match host UID/GID)
FILE_OWNER_UID=1000
FILE_OWNER_GID=1000
```

### Port Conflicts

If port 6274 is already in use, edit `docker-compose.prod.yml`:

```yaml
ports:
  - "8080:80"  # Change external port to 8080
```

Then access at `http://localhost:8080`.

### Resource Limits

Adjust CPU/memory in `docker-compose.prod.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '8.0'     # Increase for more powerful hardware
      memory: 16G
    reservations:
      cpus: '2.0'
      memory: 4G
```

---

## Updating the Deployment

### Code Updates

Since the image is immutable (code baked in):

1. Pull/commit your changes
2. Rebuild the image:

   ```bash
   ./scripts/docker-deploy.sh build
   ```

3. Restart the container:

   ```bash
   ./scripts/docker-deploy.sh restart
   ```

### Dependency Updates

Python dependencies are cached in the `agent_mahoo_venv` volume. To force a refresh:

```bash
docker volume rm agent_mahoo_venv
./scripts/docker-deploy.sh build
./scripts/docker-deploy.sh start
```

---

## Volume Management

### Backup Volumes

```bash
# Backup data volume
docker run --rm -v agent_mahoo_data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/agent_mahoo_data_backup.tar.gz /data

# Backup logs volume
docker run --rm -v agent_mahoo_logs:/logs -v $(pwd):/backup \
  ubuntu tar czf /backup/agent_mahoo_logs_backup.tar.gz /logs
```

### Restore Volumes

```bash
# Restore data volume
docker volume create agent_mahoo_data
docker run --rm -v agent_mahoo_data:/data -v $(pwd):/backup \
  ubuntu tar xzf /backup/agent_mahoo_data_backup.tar.gz -C /

# Restore logs volume
docker volume create agent_mahoo_logs
docker run --rm -v agent_mahoo_logs:/logs -v $(pwd):/backup \
  ubuntu tar xzf /backup/agent_mahoo_logs_backup.tar.gz -C /
```

### Inspect Volume Contents

```bash
# List files in data volume
docker run --rm -v agent_mahoo_data:/data ubuntu ls -lah /data

# Check SQLite databases
docker run --rm -v agent_mahoo_data:/data ubuntu \
  find /data -name "*.db" -exec ls -lh {} \;
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs for errors
./scripts/docker-deploy.sh logs

# Verify mounts
ls -ld /mnt/wdblack ~/.ssh ~/.config

# Check volume status
docker volume ls | grep agent_mahoo
```

### Health check failing

```bash
# Check health status
docker inspect agent-mahoo-production | grep -A 10 Health

# Manual health check
curl http://localhost:6274/health

# Check if port is bound
netstat -tuln | grep 6274
```

### Permission issues with mounted drives

```bash
# Check UID/GID match
id -u  # Should match FILE_OWNER_UID in .env
id -g  # Should match FILE_OWNER_GID in .env

# Fix permissions on host
sudo chown -R $(id -u):$(id -g) /mnt/wdblack/data
```

### SSH keys not working

```bash
# Verify SSH keys are mounted read-only
docker exec agent-mahoo-production ls -lah /root/.ssh

# Check permissions (should be 600 for private keys)
docker exec agent-mahoo-production stat /root/.ssh/id_rsa
```

### Out of disk space

```bash
# Check volume sizes
docker system df -v

# Clean up old images
docker image prune -a

# Remove stopped containers
docker container prune
```

---

## Security Considerations

1. **SSH Keys**: Mounted read-only (`ro`) to prevent container from modifying host keys
2. **Environment Variables**: Sensitive keys in `.env` (gitignored)
3. **Network**: Container has `host.docker.internal` access for Ollama, but external network is isolated unless explicitly configured
4. **File Permissions**: `FILE_OWNER_UID`/`FILE_OWNER_GID` should match host user to prevent permission escalation
5. **Volume Isolation**: Data volumes are container-scoped; use external backup strategy for DR

---

## Development vs. Production

| Feature | Development (`docker-compose.yml`) | Production (`docker-compose.prod.yml`) |
|---------|-----------------------------------|----------------------------------------|
| **Code** | Mounted at `/aj` (hot-reload) | Baked into image (immutable) |
| **Port** | 5000 | 6274 |
| **Restart** | `unless-stopped` | `unless-stopped` |
| **Resources** | Unlimited | 4 CPU / 8GB RAM limit |
| **Mode** | `AGENT_MAHOO_RUN_MODE=local-lite` | `AGENT_MAHOO_RUN_MODE=production` |
| **Drive Access** | Full source mount | Data mounts only |
| **Rebuild** | Not needed for code changes | Required for code changes |

Use development mode for fast iteration. Use production mode for stable deployments.

---

## Next Steps

- **Agent Mesh Integration**: Set `AGENTMESH_REDIS_URL` and `AIOS_BASE_URL` in `.env` to connect to Mahoosuc OS
- **Monitoring**: Set up external monitoring of the `/health` endpoint
- **Backups**: Schedule automated backups of the Docker volumes
- **Reverse Proxy**: Put Nginx or Caddy in front for SSL/TLS termination
- **CI/CD**: Integrate `docker-deploy.sh build` into your CI pipeline

---

## Support

- **Logs**: `./scripts/docker-deploy.sh logs`
- **Status**: `./scripts/docker-deploy.sh status`
- **GitHub Issues**: <https://github.com/mahoosuc-solutions/agent-mahoo/issues>
- **Documentation**: <https://agent-mahoo.com/documentation>
