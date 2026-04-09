# Docker Quick Reference

## Production Deployment

```bash
# Full deployment (build + start)
./scripts/docker-deploy.sh deploy

# Individual commands
./scripts/docker-deploy.sh build      # Build image
./scripts/docker-deploy.sh start      # Start container
./scripts/docker-deploy.sh stop       # Stop container
./scripts/docker-deploy.sh restart    # Restart
./scripts/docker-deploy.sh logs       # Follow logs
./scripts/docker-deploy.sh status     # Show status
```

## Access

- **WebUI**: <http://localhost:6274>
- **Health**: <http://localhost:6274/health>
- **AgentMesh Health**: <http://localhost:6274/health_agentmesh>

## Files

- **Dockerfile**: `Dockerfile.prod`
- **Compose**: `docker-compose.prod.yml`
- **Deploy Script**: `scripts/docker-deploy.sh`
- **Full Docs**: `docs/DOCKER-DEPLOY.md`

## Volumes

- `agent_mahoo_data` → `/aj/data` (SQLite, uploads)
- `agent_mahoo_logs` → `/aj/logs` (application logs)
- `agent_mahoo_venv` → `/opt/venv-a0` (Python deps)

## Mounts

- `/mnt/wdblack` → Full drive access
- `~/.ssh` → SSH keys (read-only)
- `~/.config` → User configs

## Development Mode

```bash
# Use docker-compose.yml for hot-reload dev mode
docker-compose up -d      # Port 5000, mounted source
docker-compose logs -f    # Follow logs
docker-compose down       # Stop
```

## Troubleshooting

```bash
# Check container logs
docker logs -f agent-mahoo-production

# Check health
curl http://localhost:6274/health

# Inspect volumes
docker volume inspect agent_mahoo_data

# Shell into container
docker exec -it agent-mahoo-production bash

# Check resource usage
docker stats agent-mahoo-production
```

## Code Updates

Production mode requires rebuild:

```bash
git pull
./scripts/docker-deploy.sh build
./scripts/docker-deploy.sh restart
```

Development mode auto-reloads.
