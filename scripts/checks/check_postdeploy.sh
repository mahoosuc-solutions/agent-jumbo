#!/usr/bin/env bash
# ============================================
# Post-Deploy Check: Health Verification
# ============================================
# Gate tier: SOFT BLOCK (triggers rollback on failure)
#
# Verifies that the agent-jumbo container is healthy
# and the AgentMesh bridge is connected after deploy.
#
# Usage: check_postdeploy.sh [container-name] [--timeout SECONDS]

set -euo pipefail

CONTAINER_NAME="${1:-agent-jumbo-production}"
TIMEOUT=120
INTERVAL=10

shift || true
while [[ $# -gt 0 ]]; do
    case "$1" in
        --timeout) TIMEOUT="$2"; shift 2 ;;
        *) shift ;;
    esac
done

ATTEMPTS=$((TIMEOUT / INTERVAL))

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "━━━ Post-Deploy Health Verification ━━━"
echo "  Container: ${CONTAINER_NAME}"
echo "  Timeout:   ${TIMEOUT}s (${ATTEMPTS} attempts @ ${INTERVAL}s)"
echo ""

# ── Container health check ───────────────────────────────────────────────────
HEALTH_OK=false
for i in $(seq 1 "${ATTEMPTS}"); do
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "not_found")

    if [[ "${HEALTH}" == "healthy" ]]; then
        HEALTH_OK=true
        echo -e "  ${GREEN}[OK]${NC}    Docker health: healthy (attempt ${i}/${ATTEMPTS})"
        break
    fi
    echo -e "  ${YELLOW}[WAIT]${NC}  Docker health: ${HEALTH} (attempt ${i}/${ATTEMPTS})"
    sleep "${INTERVAL}"
done

if [[ "${HEALTH_OK}" == "false" ]]; then
    echo -e "  ${RED}[FAIL]${NC}  Docker health check timed out after ${TIMEOUT}s"
    exit 1
fi

# ── /health endpoint ─────────────────────────────────────────────────────────
HEALTH_RESP=$(docker exec "${CONTAINER_NAME}" curl -sf http://localhost/health 2>/dev/null || echo "")
if echo "${HEALTH_RESP}" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('ok') else 1)" 2>/dev/null; then
    echo -e "  ${GREEN}[OK]${NC}    /health endpoint: ok"
else
    echo -e "  ${RED}[FAIL]${NC}  /health endpoint: not ok"
    echo "  Response: ${HEALTH_RESP}"
    exit 1
fi

# ── /health_agentmesh endpoint ───────────────────────────────────────────────
MESH_RESP=$(docker exec "${CONTAINER_NAME}" curl -sf http://localhost/health_agentmesh 2>/dev/null || echo "{}")
MESH_CONNECTED=$(echo "${MESH_RESP}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('connected', False))" 2>/dev/null || echo "unknown")

if [[ "${MESH_CONNECTED}" == "True" ]]; then
    echo -e "  ${GREEN}[OK]${NC}    AgentMesh bridge: connected"
else
    echo -e "  ${YELLOW}[WARN]${NC}  AgentMesh bridge: ${MESH_CONNECTED} (advisory — deploy continues)"
fi

# ── /agentmesh_validate endpoint ─────────────────────────────────────────────
VALIDATE_RESP=$(docker exec "${CONTAINER_NAME}" curl -sf -X POST http://localhost/agentmesh_validate 2>/dev/null || echo "{}")
VALIDATE_STATUS=$(echo "${VALIDATE_RESP}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "unknown")

if [[ "${VALIDATE_STATUS}" == "ok" ]]; then
    echo -e "  ${GREEN}[OK]${NC}    AgentMesh validate: ok"
elif [[ "${VALIDATE_STATUS}" == "degraded" ]]; then
    echo -e "  ${YELLOW}[WARN]${NC}  AgentMesh validate: degraded (advisory)"
else
    echo -e "  ${YELLOW}[WARN]${NC}  AgentMesh validate: ${VALIDATE_STATUS} (advisory)"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}Post-deploy verification passed${NC}"
exit 0
