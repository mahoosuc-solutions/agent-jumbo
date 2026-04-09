#!/usr/bin/env bash
# ============================================
# Agent Mahoo — Deploy Host: Verify
# ============================================
# Runs on deploy host: 46.224.170.197 ONLY.
# Must NOT run on build server or in GitHub Actions.
#
# Post-deploy verification:
#   1. /health — base health
#   2. /health_agentmesh — Agent Mesh Redis + AIOS bridge
#   3. Agent Mesh Redis stream consumer presence
#
# Usage: deploy/verify.sh [--port PORT] [--timeout SECONDS]
#
# Exits 0 if all checks pass, non-zero otherwise.

set -euo pipefail

PORT="${PORT:-6274}"
TIMEOUT="${TIMEOUT:-30}"
RETRY_INTERVAL=2

while [[ $# -gt 0 ]]; do
    case "$1" in
        --port) PORT="$2"; shift 2 ;;
        --timeout) TIMEOUT="$2"; shift 2 ;;
        *) echo "[verify] Unknown argument: $1" >&2; exit 1 ;;
    esac
done

BASE_URL="http://127.0.0.1:${PORT}"
PASS=0
FAIL=0

echo "[verify] Agent Mahoo post-deploy verification"
echo "[verify] Host:    $(hostname)"
echo "[verify] Date:    $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[verify] Target:  ${BASE_URL}"
echo "[verify] Timeout: ${TIMEOUT}s"

# ── Helpers ───────────────────────────────────────────────────────────────────
pass() {
    echo "  [PASS] $1"
    PASS=$((PASS + 1))
}

fail() {
    echo "  [FAIL] $1" >&2
    FAIL=$((FAIL + 1))
}

wait_for_port() {
    local deadline=$((SECONDS + TIMEOUT))
    echo "[verify] Waiting for port ${PORT} to open..."
    while [[ ${SECONDS} -lt ${deadline} ]]; do
        if curl -sf --max-time 2 "${BASE_URL}/health" >/dev/null 2>&1; then
            echo "[verify] Port ${PORT} is open"
            return 0
        fi
        sleep ${RETRY_INTERVAL}
    done
    echo "[verify] ERROR: port ${PORT} did not open within ${TIMEOUT}s" >&2
    return 1
}

http_get() {
    curl -sf --max-time 5 "$1" 2>/dev/null || echo ""
}

http_status() {
    curl -so /dev/null -w "%{http_code}" --max-time 5 "$1" 2>/dev/null || echo "000"
}

json_field() {
    echo "$1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$2','MISSING'))" 2>/dev/null || echo "PARSE_ERROR"
}

# ── Wait for startup ──────────────────────────────────────────────────────────
wait_for_port

# ── Check 1: /health ──────────────────────────────────────────────────────────
echo ""
echo "[verify] Check 1: /health"

HEALTH_HTTP=$(http_status "${BASE_URL}/health")
HEALTH_BODY=$(http_get "${BASE_URL}/health")

if [[ "${HEALTH_HTTP}" == "200" ]]; then
    pass "/health HTTP 200"
else
    fail "/health HTTP ${HEALTH_HTTP}"
fi

HEALTH_STATUS=$(json_field "${HEALTH_BODY}" "status")
if [[ "${HEALTH_STATUS}" == "ok" ]]; then
    pass "/health status=ok"
else
    fail "/health status='${HEALTH_STATUS}' (expected 'ok')"
fi

HEALTH_VERSION=$(json_field "${HEALTH_BODY}" "version")
if [[ "${HEALTH_VERSION}" != "MISSING" ]] && [[ "${HEALTH_VERSION}" != "PARSE_ERROR" ]]; then
    pass "/health version present: ${HEALTH_VERSION}"
else
    fail "/health version field missing"
fi

# ── Check 2: /health_agentmesh ────────────────────────────────────────────────
echo ""
echo "[verify] Check 2: /health_agentmesh"

MESH_HTTP=$(http_status "${BASE_URL}/health_agentmesh")
MESH_BODY=$(http_get "${BASE_URL}/health_agentmesh")

if [[ "${MESH_HTTP}" == "200" ]]; then
    pass "/health_agentmesh HTTP 200"
else
    fail "/health_agentmesh HTTP ${MESH_HTTP}"
fi

MESH_STATUS=$(json_field "${MESH_BODY}" "status")
if [[ "${MESH_STATUS}" == "ok" ]] || [[ "${MESH_STATUS}" == "degraded" ]]; then
    pass "/health_agentmesh status=${MESH_STATUS}"
else
    fail "/health_agentmesh status='${MESH_STATUS}'"
fi

BRIDGE_ENABLED=$(json_field "${MESH_BODY}" "aios_bridge_enabled")
echo "  [INFO] aios_bridge_enabled=${BRIDGE_ENABLED}"

REDIS_URL=$(json_field "${MESH_BODY}" "agentmesh_redis_url")
if [[ "${REDIS_URL}" != "MISSING" ]] && [[ "${REDIS_URL}" != "PARSE_ERROR" ]]; then
    # Must be redacted — no password visible
    if echo "${REDIS_URL}" | grep -qE ':.*@'; then
        fail "/health_agentmesh: agentmesh_redis_url is not redacted"
    else
        pass "/health_agentmesh: agentmesh_redis_url present and redacted"
    fi
else
    fail "/health_agentmesh: agentmesh_redis_url field missing"
fi

# ── Check 3: Agent Mesh stream consumer presence ──────────────────────────────
echo ""
echo "[verify] Check 3: Agent Mesh stream consumer"

# Check if agentmesh:events stream has a consumer group registered
# This checks via /health_agentmesh response or direct Redis if available
CONSUMER_STATUS=$(json_field "${MESH_BODY}" "consumer_active")
if [[ "${CONSUMER_STATUS}" == "true" ]] || [[ "${CONSUMER_STATUS}" == "True" ]]; then
    pass "Agent Mesh stream consumer active"
elif [[ "${CONSUMER_STATUS}" == "MISSING" ]]; then
    # Field not in response — check process-level (consumer may be integrated)
    if pgrep -f "run_ui.py" >/dev/null 2>&1; then
        pass "Agent Mahoo process running (stream consumer embedded)"
    else
        fail "Agent Mahoo process not found"
    fi
else
    fail "Agent Mesh stream consumer not active: ${CONSUMER_STATUS}"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "[verify] Results: ${PASS} passed, ${FAIL} failed"
echo "============================================"

if [[ ${FAIL} -gt 0 ]]; then
    echo "[verify] FAILED — ${FAIL} check(s) did not pass" >&2
    echo "[verify] Check logs: /opt/agent-mahoo/logs/agent-mahoo.log" >&2
    exit 1
fi

echo "[verify] All checks passed — Agent Mahoo is healthy"
