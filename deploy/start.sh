#!/usr/bin/env bash
# ============================================
# Agent Mahoo — Deploy Host: Start
# ============================================
# Runs on deploy host: 46.224.170.197 ONLY.
# Must NOT run on build server or in GitHub Actions.
#
# Extracts the approved artifact into the install
# directory and starts Agent Mahoo with resolved
# runtime env.
#
# Usage:
#   deploy/start.sh [options]
#
# Options:
#   --artifact FILE       Path to .tar.gz artifact (default: auto-detect in staging dir)
#   --env FILE            Path to runtime .env file (default: /opt/agent-mahoo/runtime.env)
#   --install-dir DIR     Installation directory (default: /opt/agent-mahoo/current)
#   --staging-dir DIR     Staging directory (default: /opt/agent-mahoo/staging)
#   --port PORT           Port to listen on (default: 6274)
#
# Exits non-zero on extraction failure or startup failure.

set -euo pipefail

ENV_FILE="${ENV_FILE:-/opt/agent-mahoo/runtime.env}"
INSTALL_DIR="${INSTALL_DIR:-/opt/agent-mahoo/current}"
STAGING_DIR="${STAGING_DIR:-/opt/agent-mahoo/staging}"
ARTIFACT_FILE=""
PORT="${PORT:-6274}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --artifact) ARTIFACT_FILE="$2"; shift 2 ;;
        --env) ENV_FILE="$2"; shift 2 ;;
        --install-dir) INSTALL_DIR="$2"; shift 2 ;;
        --staging-dir) STAGING_DIR="$2"; shift 2 ;;
        --port) PORT="$2"; shift 2 ;;
        *) echo "[start] Unknown argument: $1" >&2; exit 1 ;;
    esac
done

echo "[start] Agent Mahoo deploy start"
echo "[start] Host: $(hostname)"
echo "[start] Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ── Safety: confirm we are on the deploy host ─────────────────────────────────
BUILD_SERVER_IP="49.13.125.252"
LOCAL_IPS=$(hostname -I 2>/dev/null || true)
for ip in ${LOCAL_IPS}; do
    if [[ "${ip}" == "${BUILD_SERVER_IP}" ]]; then
        echo "[start] ERROR: this script must not run on the build server (${BUILD_SERVER_IP})" >&2
        exit 1
    fi
done

# ── Locate artifact ───────────────────────────────────────────────────────────
if [[ -z "${ARTIFACT_FILE}" ]]; then
    # Auto-detect from staging dir
    ARTIFACT_FILE=$(ls -t "${STAGING_DIR}"/agent-mahoo-*.tar.gz 2>/dev/null | head -1 || true)
    if [[ -z "${ARTIFACT_FILE}" ]]; then
        echo "[start] ERROR: no artifact found in ${STAGING_DIR}" >&2
        echo "[start] Run deploy/fetch-artifact.sh first" >&2
        exit 1
    fi
    echo "[start] Auto-detected artifact: ${ARTIFACT_FILE}"
fi

if [[ ! -f "${ARTIFACT_FILE}" ]]; then
    echo "[start] ERROR: artifact not found: ${ARTIFACT_FILE}" >&2
    exit 1
fi

# ── Validate runtime env ──────────────────────────────────────────────────────
if [[ ! -f "${ENV_FILE}" ]]; then
    echo "[start] ERROR: runtime env not found: ${ENV_FILE}" >&2
    echo "[start] Run deploy/resolve-env.sh first" >&2
    exit 1
fi

# Confirm required variables are present in env file
for required in AGENTMESH_REDIS_URL AIOS_BASE_URL; do
    if ! grep -q "^${required}=" "${ENV_FILE}"; then
        echo "[start] ERROR: ${required} missing from ${ENV_FILE}" >&2
        exit 1
    fi
done

# ── Stop existing instance ────────────────────────────────────────────────────
echo "[start] Checking for running Agent Mahoo instance..."
if pgrep -f "run_ui.py" >/dev/null 2>&1; then
    echo "[start] Stopping existing instance..."
    pkill -f "run_ui.py" || true
    sleep 2
fi

# ── Extract artifact ──────────────────────────────────────────────────────────
echo "[start] Extracting to ${INSTALL_DIR}..."
rm -rf "${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}"
tar -xzf "${ARTIFACT_FILE}" --strip-components=1 -C "${INSTALL_DIR}"
echo "[start] Extraction complete"

# ── Install dependencies ──────────────────────────────────────────────────────
echo "[start] Installing Python dependencies..."
if command -v uv >/dev/null 2>&1; then
    (cd "${INSTALL_DIR}" && uv sync --frozen --no-dev 2>&1)
else
    echo "[start] ERROR: uv not found — install uv first" >&2
    exit 1
fi

# ── Start Agent Mahoo ─────────────────────────────────────────────────────────
LOG_DIR="/opt/agent-mahoo/logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/agent-mahoo.log"

echo "[start] Starting Agent Mahoo on port ${PORT}..."
(
    cd "${INSTALL_DIR}"
    # Load runtime env — do not export to shell environment beyond this subshell
    set -a
    # shellcheck source=/dev/null
    source "${ENV_FILE}"
    set +a

    export PORT="${PORT}"

    nohup uv run python run_ui.py \
        >> "${LOG_FILE}" 2>&1 &
    echo $! > /opt/agent-mahoo/agent-mahoo.pid
)

PID=$(cat /opt/agent-mahoo/agent-mahoo.pid 2>/dev/null || echo "unknown")
echo "[start] Started with PID: ${PID}"

echo ""
echo "============================================"
echo "[start] Agent Mahoo started"
echo "  PID:         ${PID}"
echo "  Port:        ${PORT}"
echo "  Install dir: ${INSTALL_DIR}"
echo "  Log:         ${LOG_FILE}"
echo "============================================"
echo ""
echo "Next: deploy/verify.sh --port ${PORT}"
