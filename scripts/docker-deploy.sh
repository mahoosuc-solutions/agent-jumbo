#!/usr/bin/env bash
# Production Docker deployment script for Agent Jumbo
# Usage: ./scripts/docker-deploy.sh [build|start|stop|restart|logs|status]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

COMPOSE_FILE="docker-compose.prod.yml"
CONTAINER_NAME="agent-jumbo-production"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if volumes exist, create if needed
ensure_volumes() {
    log_info "Checking Docker volumes..."

    VOLUMES=("agent_jumbo_data" "agent_jumbo_logs" "agent_jumbo_venv")

    for vol in "${VOLUMES[@]}"; do
        if ! docker volume inspect "$vol" &>/dev/null; then
            log_warn "Volume $vol does not exist, creating..."
            docker volume create "$vol"
            log_success "Created volume: $vol"
        else
            log_info "Volume $vol exists"
        fi
    done
}

# Check if required mounts exist
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

# Pre-deploy checks
run_predeploy_checks() {
    log_info "Running pre-deploy checks..."

    local checks_dir="$PROJECT_ROOT/scripts/checks"

    # Instrument package check
    if [[ -x "$checks_dir/check_instrument_packages.sh" ]]; then
        if ! bash "$checks_dir/check_instrument_packages.sh"; then
            log_error "Pre-deploy check failed: instrument packages"
            log_error "Run: ./scripts/checks/check_instrument_packages.sh --fix"
            exit 1
        fi
    else
        log_warn "check_instrument_packages.sh not found or not executable — skipping"
    fi

    log_success "All pre-deploy checks passed"
}

# Build the production image
build_image() {
    log_info "Building production image..."
    run_predeploy_checks
    check_mounts

    docker-compose -f "$COMPOSE_FILE" build --no-cache

    log_success "Production image built successfully"
}

# Start the container
start_container() {
    log_info "Starting Agent Jumbo production container..."
    run_predeploy_checks
    ensure_volumes
    check_mounts

    docker-compose -f "$COMPOSE_FILE" up -d

    log_success "Container started: $CONTAINER_NAME"
    log_info "Waiting for health check..."
    sleep 10

    if docker ps --filter "name=$CONTAINER_NAME" --filter "health=healthy" | grep -q "$CONTAINER_NAME"; then
        log_success "Health check passed ✓"
        log_info "Agent Jumbo is running at http://localhost:6274"
    else
        log_warn "Container is starting but health check not yet passed. Check logs with: $0 logs"
    fi
}

# Stop the container
stop_container() {
    log_info "Stopping Agent Jumbo production container..."

    docker-compose -f "$COMPOSE_FILE" down

    log_success "Container stopped"
}

# Restart the container
restart_container() {
    log_info "Restarting Agent Jumbo production container..."
    stop_container
    sleep 2
    start_container
}

# Show logs
show_logs() {
    docker-compose -f "$COMPOSE_FILE" logs -f --tail=100
}

# Show status
show_status() {
    log_info "Container status:"
    docker ps -a --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

    echo ""
    log_info "Volume status:"
    for vol in agent_jumbo_data agent_jumbo_logs agent_jumbo_venv; do
        if docker volume inspect "$vol" &>/dev/null; then
            SIZE=$(docker system df -v | grep "$vol" | awk '{print $3}')
            echo "  $vol: $SIZE"
        fi
    done

    echo ""
    log_info "Health check:"
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "not running")
    echo "  Status: $HEALTH"

    if [ "$HEALTH" = "healthy" ]; then
        echo ""
        log_success "Agent Jumbo is healthy and accessible at http://localhost:6274"
    fi
}

# Main command dispatcher
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
    deploy)
        build_image
        start_container
        ;;
    *)
        echo "Usage: $0 {build|start|stop|restart|logs|status|deploy}"
        echo ""
        echo "Commands:"
        echo "  build    - Build the production Docker image"
        echo "  start    - Start the container (creates volumes if needed)"
        echo "  stop     - Stop the container"
        echo "  restart  - Restart the container"
        echo "  logs     - Follow container logs"
        echo "  status   - Show container and volume status"
        echo "  deploy   - Build and start (full deployment)"
        exit 1
        ;;
esac
