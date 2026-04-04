#!/usr/bin/env bash
# Pre-deploy check: verify all instrument directories are valid Python packages.
#
# Catches "No module named 'instruments.custom.<name>'" errors before they
# reach Docker build or runtime. Checks:
#   1. instruments/__init__.py exists
#   2. instruments/custom/__init__.py exists
#   3. Every subdirectory of instruments/custom/ has __init__.py
#   4. Python can actually import each discovered package
#
# Usage:
#   ./scripts/checks/check_instrument_packages.sh
#   ./scripts/checks/check_instrument_packages.sh --fix   # auto-create missing __init__.py
#
# Exit codes:
#   0  All checks passed
#   1  One or more packages missing __init__.py (or import failed)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

FIX_MODE=0
if [[ "${1:-}" == "--fix" ]]; then
    FIX_MODE=1
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

check_or_fix() {
    local file="$1"
    local rel="${file#$PROJECT_ROOT/}"
    if [[ ! -f "$file" ]]; then
        if [[ "$FIX_MODE" -eq 1 ]]; then
            touch "$file"
            echo -e "${YELLOW}[FIXED]${NC}  Created $rel"
        else
            echo -e "${RED}[MISSING]${NC} $rel"
            ERRORS=$((ERRORS + 1))
        fi
    fi
}

# 1. Parent packages (instruments/custom only — default/ is not imported as a package)
check_or_fix "$PROJECT_ROOT/instruments/__init__.py"
check_or_fix "$PROJECT_ROOT/instruments/custom/__init__.py"

# 2. Every custom instrument directory
while IFS= read -r dir; do
    [[ -d "$dir" ]] || continue
    name="$(basename "$dir")"
    # Skip non-package dirs (templates, hidden dirs)
    [[ "$name" == _* ]] && continue
    check_or_fix "$dir/__init__.py"
done < <(find "$PROJECT_ROOT/instruments/custom" -maxdepth 1 -mindepth 1 -type d | sort)

# 3. Python import check for each package (only if no structural errors)
if [[ "$ERRORS" -eq 0 ]]; then
    echo -e "${GREEN}[OK]${NC}     __init__.py structure verified"

    cd "$PROJECT_ROOT"
    IMPORT_ERRORS=0

    while IFS= read -r dir; do
        [[ -d "$dir" ]] || continue
        name="$(basename "$dir")"
        [[ "$name" == _* ]] && continue
        [[ ! -f "$dir/__init__.py" ]] && continue

        result=$(python -c "import instruments.custom.${name}" 2>&1) || {
            echo -e "${RED}[IMPORT ERROR]${NC} instruments.custom.${name}: $result"
            IMPORT_ERRORS=$((IMPORT_ERRORS + 1))
        }
    done < <(find "$PROJECT_ROOT/instruments/custom" -maxdepth 1 -mindepth 1 -type d | sort)

    if [[ "$IMPORT_ERRORS" -eq 0 ]]; then
        echo -e "${GREEN}[OK]${NC}     All instrument packages import successfully"
    else
        ERRORS=$((ERRORS + IMPORT_ERRORS))
    fi
fi

# Final result
if [[ "$ERRORS" -gt 0 ]]; then
    echo ""
    echo -e "${RED}[FAIL]${NC}   $ERRORS issue(s) found. Run with --fix to auto-create missing __init__.py files."
    exit 1
else
    echo -e "${GREEN}[PASS]${NC}   Instrument package check complete"
    exit 0
fi
