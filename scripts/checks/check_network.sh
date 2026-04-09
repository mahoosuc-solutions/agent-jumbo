#!/usr/bin/env bash
# ============================================
# Pre-Deploy Check: Network Pre-Flight
# ============================================
# Gate tier: HARD for Redis, ADVISORY for AIOS
#
# Verifies network connectivity to critical services
# before starting the container.
#
# Usage: check_network.sh [runtime.env]

set -euo pipefail

ENV_FILE="${1:-/opt/agent-mahoo/runtime.env}"
ERRORS=0
WARNINGS=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_ok()   { echo -e "  ${GREEN}[OK]${NC}    $1"; }
log_fail() { echo -e "  ${RED}[FAIL]${NC}  $1"; ERRORS=$((ERRORS + 1)); }
log_warn() { echo -e "  ${YELLOW}[WARN]${NC}  $1"; WARNINGS=$((WARNINGS + 1)); }

echo "━━━ Network Pre-Flight ━━━"

# ── Redis connectivity (HARD block) ──────────────────────────────────────────
# Try to ping Redis via the Docker network
REDIS_PASSWORD=$(grep '^REDIS_PASSWORD=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2- || echo "")

if docker exec mos-redis redis-cli -a "${REDIS_PASSWORD}" ping 2>/dev/null | grep -q "PONG"; then
    log_ok "Redis PING: PONG (mos-redis via Docker network)"
else
    # Fallback: try direct connection
    if command -v redis-cli &>/dev/null; then
        if redis-cli -h 127.0.0.1 -p 6379 -a "${REDIS_PASSWORD}" ping 2>/dev/null | grep -q "PONG"; then
            log_ok "Redis PING: PONG (localhost:6379)"
        else
            log_fail "Redis unreachable (tried mos-redis Docker and localhost:6379)"
        fi
    else
        log_fail "Redis unreachable via Docker exec and redis-cli not installed"
    fi
fi

# ── AIOS API health (ADVISORY) ───────────────────────────────────────────────
AIOS_URL=$(grep '^AIOS_BASE_URL=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2- || echo "")
if [[ -n "${AIOS_URL}" ]]; then
    AIOS_HEALTH=$(curl -sf --max-time 5 "${AIOS_URL}/health" 2>/dev/null || echo "")
    if [[ -n "${AIOS_HEALTH}" ]]; then
        log_ok "AIOS API reachable: ${AIOS_URL}"
    else
        log_warn "AIOS API not reachable: ${AIOS_URL} (advisory — deploy continues)"
    fi
else
    log_warn "AIOS_BASE_URL not set — skipping AIOS check"
fi

# ── DNS resolution (ADVISORY) ────────────────────────────────────────────────
if command -v dig &>/dev/null; then
    DNS_RESULT=$(dig +short agentjumbo.mahoosuc.ai A 2>/dev/null || echo "")
    if [[ -n "${DNS_RESULT}" ]]; then
        log_ok "DNS: agentjumbo.mahoosuc.ai -> ${DNS_RESULT}"
    else
        log_warn "DNS: agentjumbo.mahoosuc.ai not resolving (advisory)"
    fi
elif command -v host &>/dev/null; then
    if host agentjumbo.mahoosuc.ai &>/dev/null; then
        log_ok "DNS: agentjumbo.mahoosuc.ai resolves"
    else
        log_warn "DNS: agentjumbo.mahoosuc.ai not resolving (advisory)"
    fi
fi

# ── Outbound HTTPS (for Telegram, LLM APIs) ─────────────────────────────────
if curl -sf --max-time 5 "https://api.telegram.org" >/dev/null 2>&1; then
    log_ok "Outbound HTTPS: api.telegram.org reachable"
else
    log_warn "Outbound HTTPS: api.telegram.org not reachable (advisory)"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
if [[ ${ERRORS} -gt 0 ]]; then
    echo -e "${RED}Network pre-flight FAILED (${ERRORS} errors, ${WARNINGS} warnings)${NC}"
    exit 1
else
    echo -e "${GREEN}Network pre-flight passed (${WARNINGS} warnings)${NC}"
    exit 0
fi
