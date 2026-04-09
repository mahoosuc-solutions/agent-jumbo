#!/usr/bin/env bash
# Post-build check: verify the built Docker image can import all instruments.
#
# Runs a Python import test INSIDE the built image (not on the host) to catch:
#   - Missing __init__.py files in the baked image
#   - .dockerignore accidentally excluding instrument source files
#   - Import-time errors in instrument __init__.py files
#   - Cross-instrument circular import issues
#
# Usage:
#   ./scripts/checks/check_image_imports.sh [image_name]
#   ./scripts/checks/check_image_imports.sh agent-mahoo:production
#
# Exit codes:
#   0  All imports succeeded
#   1  One or more imports failed

set -euo pipefail

IMAGE="${1:-agent-mahoo:production}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

log_ok()   { echo -e "${GREEN}[OK]${NC}     $1"; }
log_fail() { echo -e "${RED}[FAIL]${NC}   $1"; ERRORS=$((ERRORS + 1)); }
log_info() { echo -e "\033[0;34m[INFO]${NC}   $1"; }

log_info "Testing imports inside image: $IMAGE"
echo ""

# Generate the import test script inline — discovers all instruments dynamically
IMPORT_SCRIPT='
import sys, os, importlib, traceback

os.chdir("/aj")
sys.path.insert(0, "/aj")

errors = []
successes = []

# 1. Parent packages
for pkg in ["instruments", "instruments.custom"]:
    try:
        importlib.import_module(pkg)
        successes.append(pkg)
    except Exception as e:
        errors.append((pkg, str(e)))

# 2. All custom instrument packages
import pathlib
custom_dir = pathlib.Path("/aj/instruments/custom")
if custom_dir.exists():
    for d in sorted(custom_dir.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        if not (d / "__init__.py").exists():
            errors.append((f"instruments.custom.{d.name}", "missing __init__.py"))
            continue
        pkg = f"instruments.custom.{d.name}"
        try:
            importlib.import_module(pkg)
            successes.append(pkg)
        except Exception as e:
            errors.append((pkg, str(e).splitlines()[0]))

# 3. Key python tool imports
for mod in [
    "python.helpers.api",
    "python.helpers.work_mode.manager",
]:
    try:
        importlib.import_module(mod)
        successes.append(mod)
    except Exception as e:
        errors.append((mod, str(e).splitlines()[0]))

print(f"SUCCESSES={len(successes)}")
print(f"ERRORS={len(errors)}")
for pkg, err in errors:
    print(f"ERROR:{pkg}:{err}")
for pkg in successes:
    print(f"OK:{pkg}")
sys.exit(1 if errors else 0)
'

# Run the import test inside the image (no venv activation needed — venv is on PATH via /opt/venv-a0/bin)
OUTPUT=$(docker run --rm \
    --entrypoint /opt/venv-a0/bin/python3 \
    "$IMAGE" \
    -c "$IMPORT_SCRIPT" 2>&1) || DOCKER_EXIT=$?

DOCKER_EXIT="${DOCKER_EXIT:-0}"

# Parse output
echo "$OUTPUT" | while IFS= read -r line; do
    case "$line" in
        OK:*)
            pkg="${line#OK:}"
            echo -e "${GREEN}[OK]${NC}     $pkg"
            ;;
        ERROR:*)
            rest="${line#ERROR:}"
            pkg="${rest%%:*}"
            err="${rest#*:}"
            echo -e "${RED}[FAIL]${NC}   $pkg — $err"
            ;;
        SUCCESSES=*|ERRORS=*)
            ;;
        *)
            [[ -n "$line" ]] && echo "  $line"
            ;;
    esac
done

# Extract error count from output
ERROR_COUNT=$(echo "$OUTPUT" | grep -c "^ERROR:" || true)

echo ""
if [[ "$ERROR_COUNT" -gt 0 ]] || [[ "$DOCKER_EXIT" -ne 0 ]]; then
    echo -e "${RED}[FAIL]${NC}   $ERROR_COUNT import error(s) in built image"
    exit 1
else
    SUCCESS_COUNT=$(echo "$OUTPUT" | grep -c "^OK:" || true)
    log_ok "All $SUCCESS_COUNT packages import successfully inside $IMAGE"
    exit 0
fi
