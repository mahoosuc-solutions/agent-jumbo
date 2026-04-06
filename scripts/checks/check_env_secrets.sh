#!/usr/bin/env bash
# ============================================
# Pre-Deploy Check: Env / Secrets Validation
# ============================================
# Gate tier: HARD BLOCK
#
# Validates that the runtime.env file contains all required
# secrets and that critical services are reachable.
#
# Usage: check_env_secrets.sh [path-to-runtime.env]

set -euo pipefail

ENV_FILE="${1:-/opt/agent-jumbo/runtime.env}"
ERRORS=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_ok()   { echo -e "  ${GREEN}[OK]${NC}    $1"; }
log_fail() { echo -e "  ${RED}[FAIL]${NC}  $1"; ERRORS=$((ERRORS + 1)); }
log_warn() { echo -e "  ${YELLOW}[WARN]${NC}  $1"; }

echo "━━━ Env/Secrets Validation ━━━"

# ── Check env file exists ────────────────────────────────────────────────────
if [[ ! -f "${ENV_FILE}" ]]; then
    log_fail "Runtime env file not found: ${ENV_FILE}"
    exit 1
fi

# ── Check file permissions (should be 600 or 400) ───────────────────────────
PERMS=$(stat -c '%a' "${ENV_FILE}" 2>/dev/null || stat -f '%Lp' "${ENV_FILE}" 2>/dev/null || echo "unknown")
if [[ "${PERMS}" != "600" ]] && [[ "${PERMS}" != "400" ]]; then
    log_warn "Runtime env permissions are ${PERMS} (expected 600 or 400)"
fi

# ── Required variables ───────────────────────────────────────────────────────
REQUIRED_VARS=(
    AGENTMESH_REDIS_URL
    AIOS_BASE_URL
    AUTH_LOGIN
    AUTH_PASSWORD
    FLASK_SECRET_KEY
    REDIS_PASSWORD
)

for var in "${REQUIRED_VARS[@]}"; do
    VALUE=$(grep "^${var}=" "${ENV_FILE}" | cut -d= -f2-)
    if [[ -z "${VALUE}" ]]; then
        log_fail "Required var missing or empty: ${var}"
    else
        log_ok "${var} is set"
    fi
done

# ── Optional but recommended ─────────────────────────────────────────────────
OPTIONAL_VARS=(
    ANTHROPIC_API_KEY
    OPENAI_API_KEY
    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID
    TELEGRAM_ALERT_CHAT_ID
    LINEAR_API_KEY
    STRIPE_API_KEY
)

for var in "${OPTIONAL_VARS[@]}"; do
    VALUE=$(grep "^${var}=" "${ENV_FILE}" | cut -d= -f2-)
    if [[ -z "${VALUE}" ]]; then
        log_warn "Optional var not set: ${var}"
    else
        log_ok "${var} is set"
    fi
done

# ── Validate Telegram token ─────────────────────────────────────────────────
TELEGRAM_TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' "${ENV_FILE}" | cut -d= -f2-)
if [[ -n "${TELEGRAM_TOKEN}" ]]; then
    TG_RESP=$(curl -sf --max-time 5 "https://api.telegram.org/bot${TELEGRAM_TOKEN}/getMe" 2>/dev/null || echo "")
    if echo "${TG_RESP}" | grep -q '"ok":true'; then
        BOT_NAME=$(echo "${TG_RESP}" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['username'])" 2>/dev/null || echo "unknown")
        log_ok "Telegram bot valid: @${BOT_NAME}"
    else
        log_fail "Telegram bot token invalid or unreachable"
    fi
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
if [[ ${ERRORS} -gt 0 ]]; then
    echo -e "${RED}Env/secrets validation FAILED (${ERRORS} errors)${NC}"
    exit 1
else
    echo -e "${GREEN}Env/secrets validation passed${NC}"
    exit 0
fi
