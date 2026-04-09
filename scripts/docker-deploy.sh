#!/usr/bin/env bash
# Production Docker deployment script for Agent Mahoo
#
# Hook pipeline:
#   PRE-BUILD:   check_instrument_packages.sh  — host __init__.py structure + imports
#                check_build_context.sh         — .dockerignore filter simulation
#   BUILD:       docker-compose build
#   POST-BUILD:  check_image_imports.sh         — import test inside the built image
#   START:       docker-compose up -d
#
# Usage: ./scripts/docker-deploy.sh [build|start|stop|restart|logs|status|deploy]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

COMPOSE_FILE="docker-compose.prod.yml"
CONTAINER_NAME="agent-mahoo-production"
IMAGE_NAME="agent-mahoo:production"
CHECKS_DIR="$PROJECT_ROOT/scripts/checks"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC}    $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}    $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC}   $1"; }

run_check() {
    local script="$1"
    local label="$2"
    shift 2
    local args=("$@")

    if [[ ! -x "$script" ]]; then
        log_warn "$label: script not found or not executable — skipping ($script)"
        return 0
    fi

    if ! bash "$script" "${args[@]}"; then
        log_error "Hook FAILED: $label"
        log_error "Fix the issues above before proceeding."
        exit 1
    fi
}

# ─── Pre-build hooks ────────────────────────────────────────────────────────

run_prebuild_hooks() {
    echo ""
    echo -e "${BLUE}━━━ Pre-Build Hooks ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # 1. Host filesystem: all instruments have __init__.py, all imports resolve
    run_check \
        "$CHECKS_DIR/check_instrument_packages.sh" \
        "Instrument package structure"

    # 2. .dockerignore simulation: critical files survive the build context filter
    run_check \
        "$CHECKS_DIR/check_build_context.sh" \
        "Docker build context (.dockerignore validation)"

    log_success "All pre-build hooks passed"
    echo ""
}

# ─── Post-build hooks ───────────────────────────────────────────────────────

run_postbuild_hooks() {
    echo ""
    echo -e "${BLUE}━━━ Post-Build Hooks ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # 3. Import test inside the built image
    run_check \
        "$CHECKS_DIR/check_image_imports.sh" \
        "Image import validation" \
        "$IMAGE_NAME"

    log_success "All post-build hooks passed"
    echo ""
}

# ─── Infrastructure checks ──────────────────────────────────────────────────

ensure_volumes() {
    log_info "Checking Docker volumes..."
    local volumes=("agent_mahoo_data" "agent_mahoo_logs" "agent_mahoo_venv")
    for vol in "${volumes[@]}"; do
        if ! docker volume inspect "$vol" &>/dev/null; then
            log_warn "Volume $vol does not exist, creating..."
            docker volume create "$vol"
            log_success "Created volume: $vol"
        else
            log_info "Volume $vol exists"
        fi
    done
}

check_mounts() {
    log_info "Checking mount points..."
    if [ ! -d "/mnt/wdblack" ]; then
        log_error "/mnt/wdblack not found. Is the WD Black drive mounted?"
        exit 1
    fi
    if [ ! -d "$HOME/.ssh" ]; then
        log_warn "$HOME/.ssh not found. SSH functionality may not work."
    fi
    if [ ! -d "$HOME/.config" ]; then
        log_warn "$HOME/.config not found. User configs will not be available."
    fi
    log_success "Mount point checks complete"
}

# ─── Build ──────────────────────────────────────────────────────────────────

build_image() {
    log_info "Building production image..."

    run_prebuild_hooks
    check_mounts

    docker-compose -f "$COMPOSE_FILE" build --no-cache

    log_success "Production image built"

    run_postbuild_hooks
}

# ─── Start ──────────────────────────────────────────────────────────────────

start_container() {
    log_info "Starting Agent Mahoo production container..."

    ensure_volumes
    check_mounts

    docker-compose -f "$COMPOSE_FILE" up -d

    log_success "Container started: $CONTAINER_NAME"
    log_info "Waiting for health check (90s startup window)..."
    sleep 10

    if docker ps --filter "name=$CONTAINER_NAME" --filter "health=healthy" | grep -q "$CONTAINER_NAME"; then
        log_success "Health check passed ✓"
        log_info "Agent Mahoo is running at http://localhost:6274"
    else
        log_warn "Container is starting but health check not yet passed."
        log_warn "Check logs with: $0 logs"
    fi
}

# ─── Stop / Restart ─────────────────────────────────────────────────────────

stop_container() {
    log_info "Stopping Agent Mahoo production container..."
    docker-compose -f "$COMPOSE_FILE" down
    log_success "Container stopped"
}

restart_container() {
    log_info "Restarting Agent Mahoo production container..."
    stop_container
    sleep 2
    start_container
}

# ─── Observability ──────────────────────────────────────────────────────────

show_logs() {
    docker-compose -f "$COMPOSE_FILE" logs -f --tail=100
}

show_status() {
    log_info "Container status:"
    docker ps -a --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

    echo ""
    log_info "Volume status:"
    for vol in agent_mahoo_data agent_mahoo_logs agent_mahoo_venv; do
        if docker volume inspect "$vol" &>/dev/null; then
            SIZE=$(docker system df -v 2>/dev/null | grep "$vol" | awk '{print $3}' || echo "?")
            echo "  $vol: $SIZE"
        fi
    done

    echo ""
    log_info "Health check:"
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "not running")
    echo "  Status: $HEALTH"

    if [ "$HEALTH" = "healthy" ]; then
        echo ""
        log_success "Agent Mahoo is healthy at http://localhost:6274"
    fi
}

# ─── Validate (run all checks without building/deploying) ───────────────────

validate() {
    echo ""
    echo -e "${BLUE}━━━ Validation Only (no build/deploy) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    run_check "$CHECKS_DIR/check_instrument_packages.sh" "Instrument package structure"
    run_check "$CHECKS_DIR/check_build_context.sh"       "Docker build context"
    if docker image inspect "$IMAGE_NAME" &>/dev/null; then
        run_check "$CHECKS_DIR/check_image_imports.sh" "Image import validation" "$IMAGE_NAME"
    else
        log_warn "Image $IMAGE_NAME not found — skipping image import check"
    fi
    log_success "Validation complete"
}

# ─── Dispatch ───────────────────────────────────────────────────────────────

case "${1:-}" in
    build)
        build_image
        ;;
    start)
        start_container
        ;;
    stop)
        stop_container
        ;;
    restart)
        restart_container
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    validate)
        validate
        ;;
    deploy)
        build_image
        start_container
        ;;
    *)
        echo "Usage: $0 {build|start|stop|restart|logs|status|validate|deploy}"
        echo ""
        echo "Commands:"
        echo "  build     Build the production Docker image (pre+post hooks)"
        echo "  start     Start the container"
        echo "  stop      Stop the container"
        echo "  restart   Restart the container"
        echo "  logs      Follow container logs"
        echo "  status    Show container, volume, and health status"
        echo "  validate  Run all checks without building or deploying"
        echo "  deploy    Full deployment: build + start"
        exit 1
        ;;
esac
