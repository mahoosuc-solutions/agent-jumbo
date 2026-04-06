#!/usr/bin/env bash
# ============================================
# Agent Jumbo — Deploy Host: Resolve Runtime Env
# ============================================
# Runs on deploy host: 46.224.170.197 ONLY.
# Must NOT run on build server or in GitHub Actions.
#
# Resolves Vault-backed runtime configuration via AppRole
# and writes a runtime .env file for Agent Jumbo.
#
# Auth modes (in priority order):
#   1. AppRole: VAULT_ROLE_ID + VAULT_SECRET_ID  (staging/production — required)
#   2. Token:   VAULT_TOKEN                       (break-glass/local-dev only)
#
# Usage: deploy/resolve-env.sh [--output FILE]
#
# Environment (required for AppRole):
#   VAULT_ADDR       Vault server address
#   VAULT_ROLE_ID    AppRole role ID
#   VAULT_SECRET_ID  AppRole secret ID
#
# Environment (break-glass only):
#   VAULT_TOKEN      Direct token (logs a warning)
#
# Optional:
#   VAULT_NAMESPACE  Vault namespace (if using HCP Vault)
#   VAULT_MOUNT      KV mount (default: secret)
#   ENV_OUTPUT       Output file path (default: /opt/agent-jumbo/runtime.env)
#
# Exits non-zero if Vault is unreachable or required secrets missing.

set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-}"
VAULT_MOUNT="${VAULT_MOUNT:-secret}"
ENV_OUTPUT="${ENV_OUTPUT:-/opt/agent-jumbo/runtime.env}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) ENV_OUTPUT="$2"; shift 2 ;;
        --vault-addr) VAULT_ADDR="$2"; shift 2 ;;
        *) echo "[resolve-env] Unknown argument: $1" >&2; exit 1 ;;
    esac
done

echo "[resolve-env] Agent Jumbo runtime env resolution"
echo "[resolve-env] Host: $(hostname)"
echo "[resolve-env] Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ── Safety: confirm we are on the deploy host ─────────────────────────────────
BUILD_SERVER_IP="49.13.125.252"
LOCAL_IPS=$(hostname -I 2>/dev/null || true)
for ip in ${LOCAL_IPS}; do
    if [[ "${ip}" == "${BUILD_SERVER_IP}" ]]; then
        echo "[resolve-env] ERROR: this script must not run on the build server (${BUILD_SERVER_IP})" >&2
        exit 1
    fi
done

# ── Validate Vault address ────────────────────────────────────────────────────
if [[ -z "${VAULT_ADDR}" ]]; then
    echo "[resolve-env] ERROR: VAULT_ADDR is required" >&2
    exit 1
fi
export VAULT_ADDR

# ── Determine auth mode ───────────────────────────────────────────────────────
AUTH_MODE=""

if [[ -n "${VAULT_ROLE_ID:-}" ]] && [[ -n "${VAULT_SECRET_ID:-}" ]]; then
    AUTH_MODE="approle"
    echo "[resolve-env] Auth mode: AppRole"
elif [[ -n "${VAULT_TOKEN:-}" ]]; then
    AUTH_MODE="token"
    echo "[resolve-env] WARNING: using VAULT_TOKEN — this is break-glass / local-dev only" >&2
    echo "[resolve-env] WARNING: AppRole must be used for staging and production" >&2
else
    echo "[resolve-env] ERROR: no Vault auth configured." >&2
    echo "[resolve-env]   Set VAULT_ROLE_ID + VAULT_SECRET_ID for AppRole (preferred)" >&2
    echo "[resolve-env]   Set VAULT_TOKEN for break-glass only" >&2
    exit 1
fi

# ── Authenticate via AppRole ──────────────────────────────────────────────────
if [[ "${AUTH_MODE}" == "approle" ]]; then
    echo "[resolve-env] Logging in via AppRole..."
    LOGIN_RESPONSE=$(curl -sf \
        --max-time 10 \
        -X POST \
        "${VAULT_ADDR}/v1/auth/approle/login" \
        -H "Content-Type: application/json" \
        -d "{\"role_id\": \"${VAULT_ROLE_ID}\", \"secret_id\": \"${VAULT_SECRET_ID}\"}")

    VAULT_TOKEN=$(echo "${LOGIN_RESPONSE}" | python3 -c \
        "import sys,json; d=json.load(sys.stdin); print(d['auth']['client_token'])")

    if [[ -z "${VAULT_TOKEN}" ]]; then
        echo "[resolve-env] ERROR: AppRole login failed — empty token" >&2
        exit 1
    fi
    TOKEN_TTL=$(echo "${LOGIN_RESPONSE}" | python3 -c \
        "import sys,json; d=json.load(sys.stdin); print(d['auth'].get('lease_duration','unknown'))" 2>/dev/null || echo "unknown")
    echo "[resolve-env] AppRole login successful (TTL: ${TOKEN_TTL}s)"
fi

export VAULT_TOKEN

# ── Helper: read a KV v2 secret ───────────────────────────────────────────────
vault_read() {
    local path="$1"
    curl -sf \
        --max-time 10 \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        "${VAULT_ADDR}/v1/${VAULT_MOUNT}/data/${path}"
}

vault_get_field() {
    local response="$1"
    local field="$2"
    echo "${response}" | python3 -c \
        "import sys,json; d=json.load(sys.stdin); print(d['data']['data'].get('${field}',''))" 2>/dev/null || echo ""
}

# ── Resolve Agent Jumbo runtime secrets ───────────────────────────────────────
# Path convention: secret/data/platform/system/agent-jumbo/<secret_name>
AGENT_JUMBO_PATH="platform/system/agent-jumbo/runtime"
echo "[resolve-env] Reading: ${VAULT_MOUNT}/data/${AGENT_JUMBO_PATH}"

RUNTIME_RESP=$(vault_read "${AGENT_JUMBO_PATH}" 2>/dev/null || true)

if [[ -z "${RUNTIME_RESP}" ]]; then
    echo "[resolve-env] ERROR: could not read ${AGENT_JUMBO_PATH} from Vault" >&2
    echo "[resolve-env] Verify the path exists and the AppRole policy grants read access" >&2
    exit 1
fi

# Extract required runtime values
AGENTMESH_REDIS_URL=$(vault_get_field "${RUNTIME_RESP}" "AGENTMESH_REDIS_URL")
AIOS_BASE_URL=$(vault_get_field "${RUNTIME_RESP}" "AIOS_BASE_URL")
AIOS_BRIDGE_API_KEY=$(vault_get_field "${RUNTIME_RESP}" "AIOS_BRIDGE_API_KEY")

# ── Additional secrets (LLM, integrations, auth, payments) ───────────────────
ANTHROPIC_API_KEY=$(vault_get_field "${RUNTIME_RESP}" "ANTHROPIC_API_KEY")
OPENAI_API_KEY=$(vault_get_field "${RUNTIME_RESP}" "OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN=$(vault_get_field "${RUNTIME_RESP}" "TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID=$(vault_get_field "${RUNTIME_RESP}" "TELEGRAM_CHAT_ID")
TELEGRAM_ALERT_CHAT_ID=$(vault_get_field "${RUNTIME_RESP}" "TELEGRAM_ALERT_CHAT_ID")
AUTH_LOGIN=$(vault_get_field "${RUNTIME_RESP}" "AUTH_LOGIN")
AUTH_PASSWORD=$(vault_get_field "${RUNTIME_RESP}" "AUTH_PASSWORD")
FLASK_SECRET_KEY=$(vault_get_field "${RUNTIME_RESP}" "FLASK_SECRET_KEY")
LINEAR_API_KEY=$(vault_get_field "${RUNTIME_RESP}" "LINEAR_API_KEY")
LINEAR_DEFAULT_TEAM_ID=$(vault_get_field "${RUNTIME_RESP}" "LINEAR_DEFAULT_TEAM_ID")
MOTION_API_KEY=$(vault_get_field "${RUNTIME_RESP}" "MOTION_API_KEY")
NOTION_API_KEY=$(vault_get_field "${RUNTIME_RESP}" "NOTION_API_KEY")
STRIPE_API_KEY=$(vault_get_field "${RUNTIME_RESP}" "STRIPE_API_KEY")
STRIPE_WEBHOOK_SECRET=$(vault_get_field "${RUNTIME_RESP}" "STRIPE_WEBHOOK_SECRET")
GMAIL_CLIENT_ID=$(vault_get_field "${RUNTIME_RESP}" "GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET=$(vault_get_field "${RUNTIME_RESP}" "GMAIL_CLIENT_SECRET")
REDIS_PASSWORD=$(vault_get_field "${RUNTIME_RESP}" "REDIS_PASSWORD")
MOS_JWT_SECRET=$(vault_get_field "${RUNTIME_RESP}" "MOS_JWT_SECRET")

# Validate required fields (infrastructure only — blocks deploy)
MISSING=()
[[ -z "${AGENTMESH_REDIS_URL}" ]] && MISSING+=("AGENTMESH_REDIS_URL")
[[ -z "${AIOS_BASE_URL}" ]] && MISSING+=("AIOS_BASE_URL")
[[ -z "${AUTH_LOGIN}" ]] && MISSING+=("AUTH_LOGIN")
[[ -z "${AUTH_PASSWORD}" ]] && MISSING+=("AUTH_PASSWORD")
[[ -z "${FLASK_SECRET_KEY}" ]] && MISSING+=("FLASK_SECRET_KEY")
[[ -z "${REDIS_PASSWORD}" ]] && MISSING+=("REDIS_PASSWORD")

# Warn for optional fields (LLM, Telegram, integrations — populate after deploy)
OPTIONAL_MISSING=()
[[ -z "${ANTHROPIC_API_KEY}" ]] && OPTIONAL_MISSING+=("ANTHROPIC_API_KEY")
[[ -z "${TELEGRAM_BOT_TOKEN}" ]] && OPTIONAL_MISSING+=("TELEGRAM_BOT_TOKEN")
[[ -z "${OPENAI_API_KEY}" ]] && OPTIONAL_MISSING+=("OPENAI_API_KEY")
[[ -z "${MOS_JWT_SECRET}" ]] && OPTIONAL_MISSING+=("MOS_JWT_SECRET")
if [[ ${#OPTIONAL_MISSING[@]} -gt 0 ]]; then
    echo "[resolve-env] WARNING: optional secrets not set (can be added post-deploy):" >&2
    for m in "${OPTIONAL_MISSING[@]}"; do
        echo "[resolve-env]   - ${m}" >&2
    done
fi

if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo "[resolve-env] ERROR: required secrets missing from Vault path ${AGENT_JUMBO_PATH}:" >&2
    for m in "${MISSING[@]}"; do
        echo "[resolve-env]   - ${m}" >&2
    done
    exit 1
fi

echo "[resolve-env] Resolved AGENTMESH_REDIS_URL: ${AGENTMESH_REDIS_URL//:*@/:***@}"
echo "[resolve-env] Resolved AIOS_BASE_URL: ${AIOS_BASE_URL}"
echo "[resolve-env] Resolved ${#MISSING[@]} required + optional secrets"

# ── Write runtime env file ────────────────────────────────────────────────────
OUTPUT_DIR="$(dirname "${ENV_OUTPUT}")"
mkdir -p "${OUTPUT_DIR}"

# Write with restricted permissions — this file contains secrets
(umask 0177; cat > "${ENV_OUTPUT}" <<ENVFILE
# Agent Jumbo Runtime Configuration
# Generated by deploy/resolve-env.sh at $(date -u +%Y-%m-%dT%H:%M:%SZ)
# DO NOT commit or copy this file — it contains resolved secrets.

# ── MOS integration ──────────────────────────────────────────────────────────
AGENTMESH_REDIS_URL=${AGENTMESH_REDIS_URL}
AIOS_BASE_URL=${AIOS_BASE_URL}
AIOS_BRIDGE_API_KEY=${AIOS_BRIDGE_API_KEY}
REDIS_PASSWORD=${REDIS_PASSWORD}
VAULT_ADDR=${VAULT_ADDR}

# ── LLM providers ───────────────────────────────────────────────────────────
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
OPENAI_API_KEY=${OPENAI_API_KEY}

# ── Telegram ─────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
TELEGRAM_ALERT_CHAT_ID=${TELEGRAM_ALERT_CHAT_ID}

# ── Auth ─────────────────────────────────────────────────────────────────────
AUTH_LOGIN=${AUTH_LOGIN}
AUTH_PASSWORD=${AUTH_PASSWORD}
FLASK_SECRET_KEY=${FLASK_SECRET_KEY}
MOS_JWT_SECRET=${MOS_JWT_SECRET}

# ── Integrations ─────────────────────────────────────────────────────────────
LINEAR_API_KEY=${LINEAR_API_KEY}
LINEAR_DEFAULT_TEAM_ID=${LINEAR_DEFAULT_TEAM_ID}
MOTION_API_KEY=${MOTION_API_KEY}
NOTION_API_KEY=${NOTION_API_KEY}

# ── Payments ─────────────────────────────────────────────────────────────────
STRIPE_API_KEY=${STRIPE_API_KEY}
STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET}

# ── Gmail ────────────────────────────────────────────────────────────────────
GMAIL_CLIENT_ID=${GMAIL_CLIENT_ID}
GMAIL_CLIENT_SECRET=${GMAIL_CLIENT_SECRET}

# ── Static runtime config ───────────────────────────────────────────────────
AGENT_JUMBO_RUN_MODE=production
DEPLOYMENT_MODE=cloud
AGENT_JUMBO_LAPTOP_MODE=false
CODE_EXEC_SSH_ENABLED=false
WEB_UI_PORT=80
WEB_UI_HOST=0.0.0.0
LITELLM_LOCAL_MODEL_COST_MAP=True
ENVFILE
)

# ── Revoke short-lived AppRole token ─────────────────────────────────────────
# The token has already served its purpose. Revoke it and clear from env.
if [[ "${AUTH_MODE}" == "approle" ]]; then
    curl -sf --max-time 5 \
        -X POST \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        "${VAULT_ADDR}/v1/auth/token/revoke-self" >/dev/null 2>&1 || true
fi
unset VAULT_TOKEN

echo ""
echo "============================================"
echo "[resolve-env] Runtime env written: ${ENV_OUTPUT}"
echo "  Auth mode:   ${AUTH_MODE}"
echo "  Vault addr:  ${VAULT_ADDR}"
echo "  Permissions: $(stat -c '%a' "${ENV_OUTPUT}" 2>/dev/null || stat -f '%p' "${ENV_OUTPUT}" 2>/dev/null || echo 'unknown')"
echo "============================================"
echo ""
echo "Next: deploy/start.sh --env ${ENV_OUTPUT}"
