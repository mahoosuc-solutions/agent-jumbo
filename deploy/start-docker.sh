#!/usr/bin/env bash
# ============================================
# Agent Jumbo — Deploy Host: Docker Start
# ============================================
# Runs on deploy host ONLY (mos-prod or CPX42).
# Must NOT run on build server or in GitHub Actions.
#
# Deploys agent-jumbo as a Docker container using
# docker-compose.mos-prod.yml. Includes deploy lock,
# pre/post-deploy checks, auto-rollback, and image
# retention (last 5 SHA-tagged images).
#
# Usage:
#   deploy/start-docker.sh [options]
#
# Options:
#   --image FILE          Docker image tarball to load (default: auto-detect in staging dir)
#   --env FILE            Runtime .env file (default: /opt/agent-jumbo/runtime.env)
#   --compose FILE        Compose file (default: docker-compose.mos-prod.yml)
#   --staging-dir DIR     Staging directory (default: /opt/agent-jumbo/staging)
#   --skip-resolve        Skip Vault env resolution (use existing runtime.env)
#   --skip-checks         Skip pre-deploy checks (NOT RECOMMENDED)
#
# Prerequisites:
#   - deploy/resolve-env.sh has been run (or use --skip-resolve=false)
#   - Docker image available in staging dir or already loaded
#
# Exits non-zero on any failure. Auto-rollback on post-deploy health failure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ENV_FILE="${ENV_FILE:-/opt/agent-jumbo/runtime.env}"
COMPOSE_FILE="${COMPOSE_FILE:-${PROJECT_ROOT}/docker-compose.cloud.yml}"
STAGING_DIR="${STAGING_DIR:-/opt/agent-jumbo/staging}"
IMAGE_FILE=""
SKIP_RESOLVE=false
SKIP_CHECKS=false
CONTAINER_NAME="agent-jumbo-production"
IMAGE_NAME="agent-jumbo"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[deploy]${NC}    $1"; }
log_success() { echo -e "${GREEN}[deploy]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[deploy]${NC}    $1"; }
log_error()   { echo -e "${RED}[deploy]${NC}   $1"; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --image) IMAGE_FILE="$2"; shift 2 ;;
        --env) ENV_FILE="$2"; shift 2 ;;
        --compose) COMPOSE_FILE="$2"; shift 2 ;;
        --staging-dir) STAGING_DIR="$2"; shift 2 ;;
        --skip-resolve) SKIP_RESOLVE=true; shift ;;
        --skip-checks) SKIP_CHECKS=true; shift ;;
        *) log_error "Unknown argument: $1"; exit 1 ;;
    esac
done

echo ""
echo -e "${BLUE}━━━ Agent Jumbo Docker Deploy ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_info "Host: $(hostname)"
log_info "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ── Safety: confirm we are NOT on the build server ───────────────────────────
BUILD_SERVER_IP="49.13.125.252"
LOCAL_IPS=$(hostname -I 2>/dev/null || true)
for ip in ${LOCAL_IPS}; do
    if [[ "${ip}" == "${BUILD_SERVER_IP}" ]]; then
        log_error "This script must not run on the build server (${BUILD_SERVER_IP})"
        exit 1
    fi
done

# ── Acquire deploy lock ──────────────────────────────────────────────────────
LOCKFILE="/opt/agent-jumbo/deploy.lock"
mkdir -p "$(dirname "${LOCKFILE}")"
exec 9>"${LOCKFILE}"
if ! flock -n 9; then
    log_error "Another deploy is in progress (lockfile: ${LOCKFILE})"
    exit 1
fi
log_info "Deploy lock acquired"

# ── Resolve env from Vault ───────────────────────────────────────────────────
if [[ "${SKIP_RESOLVE}" == "false" ]]; then
    log_info "Resolving runtime env from Vault..."
    if ! bash "${SCRIPT_DIR}/resolve-env.sh" --output "${ENV_FILE}"; then
        log_error "Vault env resolution failed"
        exit 1
    fi
fi

if [[ ! -f "${ENV_FILE}" ]]; then
    log_error "Runtime env not found: ${ENV_FILE}"
    log_error "Run deploy/resolve-env.sh first, or use --skip-resolve with existing file"
    exit 1
fi

# ── Locate and load Docker image ─────────────────────────────────────────────
if [[ -z "${IMAGE_FILE}" ]]; then
    IMAGE_FILE=$(ls -t "${STAGING_DIR}"/agent-jumbo-*.tar 2>/dev/null | head -1 || true)
fi

if [[ -n "${IMAGE_FILE}" ]] && [[ -f "${IMAGE_FILE}" ]]; then
    log_info "Loading Docker image from: ${IMAGE_FILE}"
    LOADED_IMAGE=$(docker load < "${IMAGE_FILE}" 2>/dev/null | grep -oP 'Loaded image: \K.*' || true)
    if [[ -z "${LOADED_IMAGE}" ]]; then
        log_error "Failed to load Docker image from ${IMAGE_FILE}"
        exit 1
    fi
    log_success "Loaded: ${LOADED_IMAGE}"

    # Extract SHA tag from loaded image
    IMAGE_SHA_TAG=$(echo "${LOADED_IMAGE}" | grep -oP ':[a-f0-9]{7,}$' || echo ":unknown")
    log_info "Image SHA tag: ${IMAGE_SHA_TAG}"
else
    log_warn "No image tarball found — using existing local image"
    if ! docker image inspect "${IMAGE_NAME}:current" &>/dev/null; then
        log_error "No image found: ${IMAGE_NAME}:current"
        log_error "Provide an image tarball via --image or stage it in ${STAGING_DIR}"
        exit 1
    fi
fi

# ── Tag management: current → previous, new → current ───────────────────────
if docker image inspect "${IMAGE_NAME}:current" &>/dev/null; then
    log_info "Tagging current image as previous..."
    docker tag "${IMAGE_NAME}:current" "${IMAGE_NAME}:previous" 2>/dev/null || true
fi

if [[ -n "${LOADED_IMAGE}" ]]; then
    docker tag "${LOADED_IMAGE}" "${IMAGE_NAME}:current"
    log_success "Tagged ${LOADED_IMAGE} as ${IMAGE_NAME}:current"
fi

# ── Pre-deploy checks ────────────────────────────────────────────────────────
if [[ "${SKIP_CHECKS}" == "false" ]]; then
    CHECKS_DIR="${PROJECT_ROOT}/scripts/checks"

    echo ""
    echo -e "${BLUE}━━━ Pre-Deploy Checks ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Stage 2: Env/secrets validation
    if [[ -x "${CHECKS_DIR}/check_env_secrets.sh" ]]; then
        log_info "Running env/secrets validation..."
        if ! bash "${CHECKS_DIR}/check_env_secrets.sh" "${ENV_FILE}"; then
            log_error "Env/secrets validation FAILED"
            exit 1
        fi
    fi

    # Stage 3: Network pre-flight
    if [[ -x "${CHECKS_DIR}/check_network.sh" ]]; then
        log_info "Running network pre-flight..."
        bash "${CHECKS_DIR}/check_network.sh" || log_warn "Network pre-flight had warnings (advisory)"
    fi

    # Stage 4: Image checks (existing hooks)
    if [[ -x "${CHECKS_DIR}/check_image_imports.sh" ]]; then
        log_info "Running image import validation..."
        if ! bash "${CHECKS_DIR}/check_image_imports.sh" "${IMAGE_NAME}:current"; then
            log_error "Image import validation FAILED"
            exit 1
        fi
    fi

    log_success "Pre-deploy checks passed"
fi

# ── Create Docker volumes if needed ──────────────────────────────────────────
for vol in agent_jumbo_data agent_jumbo_logs agent_jumbo_venv; do
    if ! docker volume inspect "$vol" &>/dev/null; then
        log_info "Creating volume: $vol"
        docker volume create "$vol"
    fi
done

# ── Stop existing container ──────────────────────────────────────────────────
if docker ps -q --filter "name=${CONTAINER_NAME}" | grep -q .; then
    log_info "Stopping existing container..."
    docker compose -f "${COMPOSE_FILE}" down --timeout 30 2>/dev/null || true
fi

# ── Start new container ──────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}━━━ Starting Container ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Source REDIS_PASSWORD from runtime.env for compose interpolation
REDIS_PASSWORD=$(grep '^REDIS_PASSWORD=' "${ENV_FILE}" | cut -d= -f2-)
export REDIS_PASSWORD

docker compose -f "${COMPOSE_FILE}" up -d
log_info "Container started, waiting for health check (90s startup window)..."

# ── Post-deploy health verification ──────────────────────────────────────────
echo ""
echo -e "${BLUE}━━━ Post-Deploy Verification ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

HEALTH_OK=false
for i in $(seq 1 12); do
    sleep 10
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "not_found")

    if [[ "${HEALTH}" == "healthy" ]]; then
        HEALTH_OK=true
        log_success "Health check passed on attempt ${i}/12"
        break
    fi
    log_info "Attempt ${i}/12: status=${HEALTH}, retrying in 10s..."
done

if [[ "${HEALTH_OK}" == "false" ]]; then
    log_error "Health check FAILED after 120 seconds"
    log_error "Initiating rollback..."

    # ── Rollback ─────────────────────────────────────────────────────────
    docker compose -f "${COMPOSE_FILE}" down --timeout 10 2>/dev/null || true

    if docker image inspect "${IMAGE_NAME}:previous" &>/dev/null; then
        docker tag "${IMAGE_NAME}:previous" "${IMAGE_NAME}:current"
        docker compose -f "${COMPOSE_FILE}" up -d
        log_warn "Rolled back to previous image"
    else
        log_error "No previous image available for rollback"
    fi

    # Send Telegram alert
    TELEGRAM_TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' "${ENV_FILE}" | cut -d= -f2-)
    ALERT_CHAT=$(grep '^TELEGRAM_ALERT_CHAT_ID=' "${ENV_FILE}" | cut -d= -f2-)
    if [[ -n "${TELEGRAM_TOKEN}" ]] && [[ -n "${ALERT_CHAT}" ]]; then
        curl -sf --max-time 10 \
            -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
            -d "chat_id=${ALERT_CHAT}" \
            -d "text=ROLLBACK: agent-jumbo deploy failed. Reverted to previous image. Host: $(hostname)" \
            >/dev/null 2>&1 || true
    fi

    exit 1
fi

# ── AgentMesh verification ───────────────────────────────────────────────────
log_info "Verifying AgentMesh bridge..."
MESH_HEALTH=$(docker exec "${CONTAINER_NAME}" curl -sf http://localhost/health_agentmesh 2>/dev/null || echo "{}")
MESH_CONNECTED=$(echo "${MESH_HEALTH}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('connected', False))" 2>/dev/null || echo "unknown")

if [[ "${MESH_CONNECTED}" == "True" ]]; then
    log_success "AgentMesh bridge connected"
else
    log_warn "AgentMesh bridge not connected (status: ${MESH_CONNECTED}) — advisory only"
fi

# ── Image retention: keep last 5 ─────────────────────────────────────────────
log_info "Pruning old images (keeping last 5)..."
OLD_IMAGES=$(docker images "${IMAGE_NAME}" --format '{{.ID}} {{.CreatedAt}}' 2>/dev/null \
    | sort -k2 -r | tail -n +6 | awk '{print $1}')
if [[ -n "${OLD_IMAGES}" ]]; then
    echo "${OLD_IMAGES}" | xargs -r docker rmi 2>/dev/null || true
    log_info "Pruned old images"
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━ Deploy Complete ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_success "Agent Jumbo is running"
log_info "Container: ${CONTAINER_NAME}"
log_info "Compose:   ${COMPOSE_FILE}"
log_info "AgentMesh: ${MESH_CONNECTED}"
echo ""
