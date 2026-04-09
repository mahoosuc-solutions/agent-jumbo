#!/usr/bin/env bash
# ============================================
# Agent Mahoo — Deploy Host: Fetch Artifact
# ============================================
# Runs on deploy host: 46.224.170.197
# Must NOT run on build server or in GitHub Actions.
#
# Retrieves the approved artifact and evidence bundle
# from the build server, verifies checksums, and
# stages files for deployment.
#
# Usage:
#   deploy/fetch-artifact.sh <artifact-id>
#   deploy/fetch-artifact.sh --from-bundle dist/evidence-bundle.json
#
# Environment:
#   BUILD_SERVER_USER    SSH user on build server (default: deploy)
#   BUILD_SERVER_HOST    Build server address (default: 49.13.125.252)
#   BUILD_SERVER_DIR     Remote dist/ path (default: ~/agent-mahoo/dist)
#   DEPLOY_STAGING_DIR   Local staging directory (default: /opt/agent-mahoo/staging)
#
# Exits non-zero on checksum failure or missing artifact.

set -euo pipefail

BUILD_SERVER_USER="${BUILD_SERVER_USER:-deploy}"
BUILD_SERVER_HOST="${BUILD_SERVER_HOST:-49.13.125.252}"
BUILD_SERVER_DIR="${BUILD_SERVER_DIR:-~/agent-mahoo/dist}"
DEPLOY_STAGING_DIR="${DEPLOY_STAGING_DIR:-/opt/agent-mahoo/staging}"

ARTIFACT_ID=""
EVIDENCE_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --from-bundle) EVIDENCE_FILE="$2"; shift 2 ;;
        --build-server-host) BUILD_SERVER_HOST="$2"; shift 2 ;;
        --staging-dir) DEPLOY_STAGING_DIR="$2"; shift 2 ;;
        -*) echo "[fetch] Unknown option: $1" >&2; exit 1 ;;
        *) ARTIFACT_ID="$1"; shift ;;
    esac
done

echo "[fetch] Agent Mahoo artifact fetch"
echo "[fetch] Host: $(hostname)"
echo "[fetch] Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ── Safety: confirm we are on the deploy host ─────────────────────────────────
BUILD_SERVER_IP="49.13.125.252"
LOCAL_IPS=$(hostname -I 2>/dev/null || true)
for ip in ${LOCAL_IPS}; do
    if [[ "${ip}" == "${BUILD_SERVER_IP}" ]]; then
        echo "[fetch] ERROR: this script must not run on the build server (${BUILD_SERVER_IP})" >&2
        exit 1
    fi
done

# ── Resolve artifact info ──────────────────────────────────────────────────────
if [[ -n "${EVIDENCE_FILE}" ]]; then
    if [[ ! -f "${EVIDENCE_FILE}" ]]; then
        echo "[fetch] ERROR: evidence file not found: ${EVIDENCE_FILE}" >&2
        exit 1
    fi
    ARTIFACT_ID=$(python3 -c "import json; d=json.load(open('${EVIDENCE_FILE}')); print(d['artifact_id'])")
    VERSION=$(python3 -c "import json; d=json.load(open('${EVIDENCE_FILE}')); print(d['version'])")
    EXPECTED_SHA=$(python3 -c "import json; d=json.load(open('${EVIDENCE_FILE}')); print(d['checksums']['targz_sha256'])")
    BRIDGE_STATUS=$(python3 -c "import json; d=json.load(open('${EVIDENCE_FILE}')); print(d['tests']['bridge_contract'])")
    echo "[fetch] Loading from evidence bundle: ${EVIDENCE_FILE}"
    echo "[fetch] Artifact ID: ${ARTIFACT_ID}"
    echo "[fetch] Bridge tests: ${BRIDGE_STATUS}"

    if [[ "${BRIDGE_STATUS}" != "passed" ]]; then
        echo "[fetch] ERROR: evidence bundle shows bridge-contract tests did not pass (${BRIDGE_STATUS})" >&2
        exit 1
    fi
elif [[ -n "${ARTIFACT_ID}" ]]; then
    # Parse version from artifact ID: agent-mahoo-<VERSION>-<SHORT_SHA>
    VERSION=$(echo "${ARTIFACT_ID}" | sed 's/^agent-mahoo-\(.*\)-[0-9a-f]\{7\}$/\1/')
    EXPECTED_SHA=""
    echo "[fetch] Artifact ID: ${ARTIFACT_ID}"
    echo "[fetch] Version: ${VERSION}"
else
    echo "[fetch] ERROR: provide <artifact-id> or --from-bundle <file>" >&2
    echo "[fetch] Usage: $0 <artifact-id>" >&2
    echo "[fetch] Usage: $0 --from-bundle dist/evidence-bundle.json" >&2
    exit 1
fi

TARGZ_NAME="agent-mahoo-${VERSION}.tar.gz"
REMOTE_TARGZ="${BUILD_SERVER_DIR}/${TARGZ_NAME}"

# ── Prepare staging directory ─────────────────────────────────────────────────
echo "[fetch] Staging directory: ${DEPLOY_STAGING_DIR}"
mkdir -p "${DEPLOY_STAGING_DIR}"

LOCAL_TARGZ="${DEPLOY_STAGING_DIR}/${TARGZ_NAME}"

# ── Fetch artifact from build server ─────────────────────────────────────────
echo "[fetch] Fetching ${TARGZ_NAME} from ${BUILD_SERVER_HOST}..."
scp -q "${BUILD_SERVER_USER}@${BUILD_SERVER_HOST}:${REMOTE_TARGZ}" "${LOCAL_TARGZ}"
echo "[fetch] Fetch complete: ${LOCAL_TARGZ}"

# Fetch evidence bundle if not already present
if [[ -z "${EVIDENCE_FILE}" ]]; then
    REMOTE_EVIDENCE="${BUILD_SERVER_DIR}/evidence-bundle.json"
    LOCAL_EVIDENCE="${DEPLOY_STAGING_DIR}/evidence-bundle.json"
    echo "[fetch] Fetching evidence bundle..."
    scp -q "${BUILD_SERVER_USER}@${BUILD_SERVER_HOST}:${REMOTE_EVIDENCE}" "${LOCAL_EVIDENCE}"
    EVIDENCE_FILE="${LOCAL_EVIDENCE}"
    EXPECTED_SHA=$(python3 -c "import json; d=json.load(open('${EVIDENCE_FILE}')); print(d['checksums']['targz_sha256'])")
    # Gate: refuse if bridge-contract tests did not pass
    BRIDGE_STATUS=$(python3 -c "import json; d=json.load(open('${EVIDENCE_FILE}')); print(d['tests']['bridge_contract'])")
    if [[ "${BRIDGE_STATUS}" != "passed" ]]; then
        echo "[fetch] ERROR: evidence bundle shows bridge-contract tests did not pass (${BRIDGE_STATUS})" >&2
        exit 1
    fi
fi

# ── Verify checksum ────────────────────────────────────────────────────────────
echo "[fetch] Verifying checksum..."
ACTUAL_SHA=$(sha256sum "${LOCAL_TARGZ}" | awk '{print $1}')

if [[ -n "${EXPECTED_SHA}" ]]; then
    if [[ "${ACTUAL_SHA}" != "${EXPECTED_SHA}" ]]; then
        echo "[fetch] ERROR: checksum mismatch for ${TARGZ_NAME}" >&2
        echo "[fetch]   expected: ${EXPECTED_SHA}" >&2
        echo "[fetch]   actual:   ${ACTUAL_SHA}" >&2
        rm -f "${LOCAL_TARGZ}"
        exit 1
    fi
    echo "[fetch] Checksum verified: ${ACTUAL_SHA}"
    CHECKSUM_VERIFIED="true"
else
    echo "[fetch] WARNING: no expected checksum to verify against" >&2
    CHECKSUM_VERIFIED="false"
fi

# ── Write local fetch record ───────────────────────────────────────────────────
cat > "${DEPLOY_STAGING_DIR}/fetch-record.json" <<RECORD
{
  "artifact_id": "${ARTIFACT_ID}",
  "version": "${VERSION}",
  "fetched_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "fetch_host": "$(hostname)",
  "source": "${BUILD_SERVER_HOST}:${REMOTE_TARGZ}",
  "local_path": "${LOCAL_TARGZ}",
  "checksum_sha256": "${ACTUAL_SHA}",
  "checksum_verified": ${CHECKSUM_VERIFIED}
}
RECORD

echo ""
echo "============================================"
echo "[fetch] Artifact ready for deployment"
echo "  Local archive: ${LOCAL_TARGZ}"
echo "  Evidence:      ${EVIDENCE_FILE}"
echo "  SHA256:        ${ACTUAL_SHA}"
echo "============================================"
echo ""
echo "Next: deploy/resolve-env.sh && deploy/start.sh"
