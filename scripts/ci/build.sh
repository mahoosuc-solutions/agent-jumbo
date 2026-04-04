#!/usr/bin/env bash
# ============================================
# Agent Jumbo — Build Server CI: Build
# ============================================
# Runs on build server: 49.13.125.252
# Must NOT run on deploy host or in GitHub Actions.
#
# Usage: scripts/ci/build.sh <commit-sha>
#
# Produces:
#   dist/agent-jumbo-<VERSION>.tar.gz
#   dist/agent-jumbo-<VERSION>.zip
#   dist/build-manifest.json
#
# Exits non-zero on any failure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"

# ── Args ────────────────────────────────────────────────────────────────────
COMMIT_SHA="${1:-}"
if [[ -z "${COMMIT_SHA}" ]]; then
    echo "[build] ERROR: commit SHA required as first argument" >&2
    echo "[build] Usage: $0 <commit-sha>" >&2
    exit 1
fi

# Validate format: 7-40 hex chars
if ! echo "${COMMIT_SHA}" | grep -qE '^[0-9a-f]{7,40}$'; then
    echo "[build] ERROR: invalid commit SHA format: ${COMMIT_SHA}" >&2
    exit 1
fi

echo "[build] Starting Agent Jumbo build"
echo "[build] Commit: ${COMMIT_SHA}"
echo "[build] Host:   $(hostname)"
echo "[build] Date:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ── Safety: confirm we are on the build server ───────────────────────────────
# Hard-coded deploy host IP — build must never run there
DEPLOY_HOST_IP="46.224.170.197"
LOCAL_IPS=$(hostname -I 2>/dev/null || true)
for ip in ${LOCAL_IPS}; do
    if [[ "${ip}" == "${DEPLOY_HOST_IP}" ]]; then
        echo "[build] ERROR: this script must not run on the deploy host (${DEPLOY_HOST_IP})" >&2
        exit 1
    fi
done

# ── Verify pinned SHA is checked out ─────────────────────────────────────────
CURRENT_SHA=$(git rev-parse HEAD)
SHORT_CURRENT="${CURRENT_SHA:0:7}"
SHORT_PINNED="${COMMIT_SHA:0:7}"

if [[ "${CURRENT_SHA}" != "${COMMIT_SHA}"* ]] && [[ "${CURRENT_SHA:0:${#COMMIT_SHA}}" != "${COMMIT_SHA}" ]]; then
    # Allow short SHA prefix match
    if [[ "${SHORT_CURRENT}" != "${SHORT_PINNED}" ]]; then
        echo "[build] ERROR: HEAD is ${CURRENT_SHA} but expected ${COMMIT_SHA}" >&2
        echo "[build] Checkout the correct commit before running build." >&2
        exit 1
    fi
fi

FULL_SHA=$(git rev-parse HEAD)
echo "[build] Verified commit: ${FULL_SHA}"

# ── Confirm no Vault / secret material is present ────────────────────────────
for forbidden in VAULT_TOKEN VAULT_ROOT_TOKEN VAULT_SECRET_ID; do
    if [[ -n "${!forbidden:-}" ]]; then
        echo "[build] ERROR: ${forbidden} must not be set on the build server" >&2
        exit 1
    fi
done

# ── Run packaging ─────────────────────────────────────────────────────────────
echo "[build] Running package-release.sh..."
bash scripts/package-release.sh

# ── Resolve VERSION from pyproject.toml ──────────────────────────────────────
VERSION=$(python3 - <<'PYEOF'
try:
    import tomllib
except (ImportError, ModuleNotFoundError):
    import tomli as tomllib
with open("pyproject.toml", "rb") as f:
    d = tomllib.load(f)
print(d["project"]["version"])
PYEOF
)

TARGZ="dist/agent-jumbo-${VERSION}.tar.gz"
ZIP="dist/agent-jumbo-${VERSION}.zip"

if [[ ! -f "${TARGZ}" ]]; then
    echo "[build] ERROR: expected artifact not found: ${TARGZ}" >&2
    exit 1
fi

# ── Checksums ────────────────────────────────────────────────────────────────
echo "[build] Computing checksums..."
TARGZ_SHA256=$(sha256sum "${TARGZ}" | awk '{print $1}')
ZIP_SHA256=$(sha256sum "${ZIP}" | awk '{print $1}')

echo "[build] ${TARGZ}: ${TARGZ_SHA256}"
echo "[build] ${ZIP}:   ${ZIP_SHA256}"

# Write checksum files
sha256sum "${TARGZ}" > "${TARGZ}.sha256"
sha256sum "${ZIP}" > "${ZIP}.sha256"

# ── Build manifest ────────────────────────────────────────────────────────────
BUILD_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
ARTIFACT_ID="agent-jumbo-${VERSION}-${FULL_SHA:0:7}"

cat > dist/build-manifest.json <<MANIFEST
{
  "artifact_id": "${ARTIFACT_ID}",
  "version": "${VERSION}",
  "commit_sha": "${FULL_SHA}",
  "built_at": "${BUILD_TS}",
  "build_host": "$(hostname)",
  "artifacts": {
    "targz": "${TARGZ}",
    "zip": "${ZIP}"
  },
  "checksums": {
    "targz_sha256": "${TARGZ_SHA256}",
    "zip_sha256": "${ZIP_SHA256}"
  },
  "status": "built"
}
MANIFEST

echo ""
echo "============================================"
echo "[build] Build complete"
echo "  Artifact ID: ${ARTIFACT_ID}"
echo "  Version:     ${VERSION}"
echo "  Commit:      ${FULL_SHA}"
echo "  tar.gz:      ${TARGZ} (${TARGZ_SHA256})"
echo "  zip:         ${ZIP} (${ZIP_SHA256})"
echo "  Manifest:    dist/build-manifest.json"
echo "============================================"
