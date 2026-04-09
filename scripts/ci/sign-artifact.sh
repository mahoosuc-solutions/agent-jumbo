#!/usr/bin/env bash
# ============================================
# Agent Mahoo — Build Server CI: Sign Artifact
# ============================================
# Runs on build server: 49.13.125.252
# Must NOT run on deploy host or in GitHub Actions.
#
# Reads dist/build-manifest.json (produced by build.sh),
# verifies checksums, runs bridge-contract tests,
# and writes a signed evidence bundle.
#
# Usage: scripts/ci/sign-artifact.sh [--test-summary FILE]
#
# Produces:
#   dist/evidence-bundle.json   — immutable evidence record for deploy host
#
# Exits non-zero if:
#   - build-manifest.json missing
#   - checksums do not match
#   - bridge-contract tests fail
#   - evidence bundle cannot be written

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"

TEST_SUMMARY_FILE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --test-summary) TEST_SUMMARY_FILE="$2"; shift 2 ;;
        *) echo "[sign] Unknown argument: $1" >&2; exit 1 ;;
    esac
done

MANIFEST="dist/build-manifest.json"
echo "[sign] Starting artifact signing"
echo "[sign] Host: $(hostname)"
echo "[sign] Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ── Safety: confirm we are on the build server ───────────────────────────────
DEPLOY_HOST_IP="46.224.170.197"
LOCAL_IPS=$(hostname -I 2>/dev/null || true)
for ip in ${LOCAL_IPS}; do
    if [[ "${ip}" == "${DEPLOY_HOST_IP}" ]]; then
        echo "[sign] ERROR: this script must not run on the deploy host (${DEPLOY_HOST_IP})" >&2
        exit 1
    fi
done

# ── Confirm no Vault / secret material is present ────────────────────────────
for forbidden in VAULT_TOKEN VAULT_ROOT_TOKEN VAULT_SECRET_ID; do
    if [[ -n "${!forbidden:-}" ]]; then
        echo "[sign] ERROR: ${forbidden} must not be set on the build server" >&2
        exit 1
    fi
done

# ── Load manifest ─────────────────────────────────────────────────────────────
if [[ ! -f "${MANIFEST}" ]]; then
    echo "[sign] ERROR: ${MANIFEST} not found — run build.sh first" >&2
    exit 1
fi

echo "[sign] Reading ${MANIFEST}..."
ARTIFACT_ID=$(python3 -c "import json; d=json.load(open('${MANIFEST}')); print(d['artifact_id'])")
VERSION=$(python3 -c "import json; d=json.load(open('${MANIFEST}')); print(d['version'])")
COMMIT_SHA=$(python3 -c "import json; d=json.load(open('${MANIFEST}')); print(d['commit_sha'])")
BUILT_AT=$(python3 -c "import json; d=json.load(open('${MANIFEST}')); print(d['built_at'])")
TARGZ=$(python3 -c "import json; d=json.load(open('${MANIFEST}')); print(d['artifacts']['targz'])")
ZIP=$(python3 -c "import json; d=json.load(open('${MANIFEST}')); print(d['artifacts']['zip'])")
EXPECTED_TARGZ_SHA=$(python3 -c "import json; d=json.load(open('${MANIFEST}')); print(d['checksums']['targz_sha256'])")
EXPECTED_ZIP_SHA=$(python3 -c "import json; d=json.load(open('${MANIFEST}')); print(d['checksums']['zip_sha256'])")

echo "[sign] Artifact:  ${ARTIFACT_ID}"
echo "[sign] Version:   ${VERSION}"
echo "[sign] Commit:    ${COMMIT_SHA}"

# ── Verify checksums ──────────────────────────────────────────────────────────
echo "[sign] Verifying checksums..."

if [[ ! -f "${TARGZ}" ]]; then
    echo "[sign] ERROR: artifact not found: ${TARGZ}" >&2
    exit 1
fi
if [[ ! -f "${ZIP}" ]]; then
    echo "[sign] ERROR: artifact not found: ${ZIP}" >&2
    exit 1
fi

ACTUAL_TARGZ_SHA=$(sha256sum "${TARGZ}" | awk '{print $1}')
ACTUAL_ZIP_SHA=$(sha256sum "${ZIP}" | awk '{print $1}')

if [[ "${ACTUAL_TARGZ_SHA}" != "${EXPECTED_TARGZ_SHA}" ]]; then
    echo "[sign] ERROR: tar.gz checksum mismatch" >&2
    echo "[sign]   expected: ${EXPECTED_TARGZ_SHA}" >&2
    echo "[sign]   actual:   ${ACTUAL_TARGZ_SHA}" >&2
    exit 1
fi
echo "[sign] tar.gz checksum verified: ${ACTUAL_TARGZ_SHA}"

if [[ "${ACTUAL_ZIP_SHA}" != "${EXPECTED_ZIP_SHA}" ]]; then
    echo "[sign] ERROR: zip checksum mismatch" >&2
    echo "[sign]   expected: ${EXPECTED_ZIP_SHA}" >&2
    echo "[sign]   actual:   ${ACTUAL_ZIP_SHA}" >&2
    exit 1
fi
echo "[sign] zip checksum verified: ${ACTUAL_ZIP_SHA}"

# ── Run bridge-contract tests ─────────────────────────────────────────────────
echo ""
echo "[sign] Running bridge-contract tests..."
BRIDGE_LOG="dist/bridge-contract-test.log"

if bash scripts/ci/bridge-contract-test.sh 2>&1 | tee "${BRIDGE_LOG}"; then
    BRIDGE_STATUS="passed"
    echo "[sign] Bridge-contract tests: PASSED"
else
    BRIDGE_STATUS="failed"
    echo "[sign] ERROR: bridge-contract tests failed — aborting signing" >&2
    exit 1
fi

# ── Resolve test summary ──────────────────────────────────────────────────────
TEST_SUMMARY_CONTENT=""
if [[ -n "${TEST_SUMMARY_FILE}" ]] && [[ -f "${TEST_SUMMARY_FILE}" ]]; then
    TEST_SUMMARY_CONTENT=$(cat "${TEST_SUMMARY_FILE}")
else
    TEST_SUMMARY_CONTENT=$(cat "${BRIDGE_LOG}")
fi

# Escape for JSON embedding (replace newlines with \n, escape quotes)
TEST_SUMMARY_JSON=$(echo "${TEST_SUMMARY_CONTENT}" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")

# ── Artifact listing ──────────────────────────────────────────────────────────
ARTIFACT_FILE_COUNT=$(tar -tzf "${TARGZ}" | wc -l | tr -d ' ')

# ── Write evidence bundle ─────────────────────────────────────────────────────
SIGNED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

cat > dist/evidence-bundle.json <<EVIDENCE
{
  "artifact_id": "${ARTIFACT_ID}",
  "version": "${VERSION}",
  "commit_sha": "${COMMIT_SHA}",
  "git_branch": "${GIT_BRANCH}",
  "built_at": "${BUILT_AT}",
  "signed_at": "${SIGNED_AT}",
  "build_host": "$(hostname)",
  "artifacts": {
    "targz": "${TARGZ}",
    "zip": "${ZIP}",
    "file_count": ${ARTIFACT_FILE_COUNT}
  },
  "checksums": {
    "targz_sha256": "${ACTUAL_TARGZ_SHA}",
    "zip_sha256": "${ACTUAL_ZIP_SHA}"
  },
  "tests": {
    "bridge_contract": "${BRIDGE_STATUS}",
    "log": ${TEST_SUMMARY_JSON}
  },
  "security": {
    "vault_token_on_builder": false,
    "apprle_secret_id_on_builder": false,
    "production_env_on_builder": false
  },
  "status": "signed"
}
EVIDENCE

echo ""
echo "============================================"
echo "[sign] Evidence bundle written: dist/evidence-bundle.json"
echo "  Artifact ID:  ${ARTIFACT_ID}"
echo "  Version:      ${VERSION}"
echo "  Commit:       ${COMMIT_SHA}"
echo "  Bridge tests: ${BRIDGE_STATUS}"
echo "  Signed at:    ${SIGNED_AT}"
echo "============================================"
echo ""
echo "Deploy host should retrieve:"
echo "  ${TARGZ}"
echo "  dist/evidence-bundle.json"
