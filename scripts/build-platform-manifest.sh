#!/usr/bin/env bash
# build-platform-manifest.sh — Generate web/public/platform-manifest.json
#
# If python3 is available, runs introspect_platform.py for live metrics.
# Otherwise falls back to the existing manifest or writes a structural stub.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MANIFEST="$ROOT_DIR/web/public/platform-manifest.json"

mkdir -p "$ROOT_DIR/web/public"

if command -v python3 &>/dev/null; then
  echo "[build-platform-manifest] Running introspect_platform.py ..."
  python3 "$SCRIPT_DIR/introspect_platform.py"
  exit 0
fi

# No python3 — fall back
if [ -f "$MANIFEST" ]; then
  echo "[build-platform-manifest] python3 not found; using existing manifest."
  exit 0
fi

echo "[build-platform-manifest] python3 not found; writing fallback stub."
cat > "$MANIFEST" <<'FALLBACK'
{"generated_at":"unknown","platform":{"commands":{"total":0,"categories":0},"instruments":{"total":0,"active":0},"tools":{"total":0},"api_endpoints":{"total":0},"integrations":[],"helper_modules":0},"github":{"repos":0,"verticals":[]},"ag_mesh":{"event_types":[],"risk_levels":[],"agent_profiles":0},"products":[],"pricing":{"tiers":[],"cost_components":[],"competitive_reference":[],"assumptions":[]}}
FALLBACK
