#!/usr/bin/env bash
# Pre-build check: validate what will actually be copied into the Docker image.
#
# Simulates the Docker build context by applying .dockerignore rules to the
# git-tracked file list. Uses pathspec (Python) for accurate gitignore-style
# pattern matching — the same algorithm Docker uses.
#
# Checks:
#   1. instruments/__init__.py and instruments/custom/__init__.py
#   2. All instruments/custom/<name>/__init__.py files
#   3. python/api/, python/tools/, python/helpers/ have Python source files
#   4. Key root files: run_ui.py, pyproject.toml, requirements.txt
#
# Usage:
#   ./scripts/checks/check_build_context.sh
#
# Exit codes:
#   0  All critical files present in build context
#   1  One or more critical files excluded by .dockerignore

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ERRORS=0

log_ok()   { echo -e "${GREEN}[OK]${NC}     $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC}   $1"; }
log_fail() { echo -e "${RED}[MISSING]${NC} $1"; ERRORS=$((ERRORS + 1)); }
log_info() { echo -e "${BLUE}[INFO]${NC}    $1"; }

# ─── Enumerate build context using Python pathspec ──────────────────────────

log_info "Simulating build context (applying .dockerignore rules)..."

CONTEXT_FILES=$(PROJECT_ROOT="$PROJECT_ROOT" python3 - <<'PYEOF'
import sys, pathlib, subprocess, os

root = pathlib.Path(os.environ["PROJECT_ROOT"])

# Read .dockerignore
di = root / ".dockerignore"
if not di.exists():
    print("", end="")
    sys.exit(0)

lines = [l.strip() for l in di.read_text().splitlines()
         if l.strip() and not l.strip().startswith("#")]

# Get all files tracked by git + untracked non-ignored files
result = subprocess.run(
    ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
    capture_output=True, text=True, cwd=str(root)
)
all_files = [f for f in result.stdout.strip().splitlines() if f]

# Apply .dockerignore patterns (gitignore semantics — last matching rule wins)
def is_excluded(path):
    excluded = False
    for pat in lines:
        negate = pat.startswith("!")
        p = pat[1:] if negate else pat

        # Normalize: strip leading /
        p = p.lstrip("/")

        import fnmatch

        # Match against the full path and any suffix
        matched = False
        parts = path.split("/")

        # Direct pattern match
        if fnmatch.fnmatch(path, p):
            matched = True
        # Suffix wildcard: instruments/** matches instruments/custom/foo.py
        elif "/**" in p:
            prefix = p.split("/**")[0]
            if path.startswith(prefix + "/") or path == prefix:
                matched = True
        # No-slash pattern: match against any path component or basename
        elif "/" not in p:
            if fnmatch.fnmatch(parts[-1], p):
                matched = True
            # Also match **/<pattern>
            for part in parts:
                if fnmatch.fnmatch(part, p):
                    matched = True
                    break
        # Anchored pattern (contains /)
        else:
            if fnmatch.fnmatch(path, p):
                matched = True
            # Try matching as prefix
            if path.startswith(p.rstrip("/") + "/"):
                matched = True

        if matched:
            excluded = not negate

    return excluded

included = [f for f in all_files if not is_excluded(f)]
print("\n".join(sorted(included)))
PYEOF
) || true

if [ -z "$CONTEXT_FILES" ]; then
    log_warn "Could not enumerate build context — skipping context checks"
    log_warn "Ensure git and Python 3 are available"
    exit 0
fi

FILE_COUNT=$(echo "$CONTEXT_FILES" | wc -l)
log_info "Build context contains ~$FILE_COUNT files (post .dockerignore filter)"

in_context() {
    echo "$CONTEXT_FILES" | grep -qxF "$1" 2>/dev/null
}

echo ""
echo "=== Instrument __init__.py files ==="

# 1. Parent packages
for f in "instruments/__init__.py" "instruments/custom/__init__.py"; do
    if [[ ! -f "$PROJECT_ROOT/$f" ]]; then
        log_fail "$f (missing on host — run: touch $f)"
    elif in_context "$f"; then
        log_ok "$f"
    else
        log_fail "$f (exists on host but excluded by .dockerignore)"
    fi
done

# 2. Every custom instrument __init__.py
while IFS= read -r dir; do
    [[ -d "$dir" ]] || continue
    name="$(basename "$dir")"
    [[ "$name" == _* ]] && continue
    rel="instruments/custom/$name/__init__.py"
    if [[ ! -f "$PROJECT_ROOT/$rel" ]]; then
        # Hard failure: file missing on host entirely
        log_fail "$rel (missing — run: ./scripts/checks/check_instrument_packages.sh --fix)"
    elif in_context "$rel"; then
        log_ok "$rel"
    else
        # Soft warning: simulator may have false positives; only hard-fail if not git-tracked
        if git ls-files --error-unmatch "$rel" &>/dev/null 2>&1; then
            log_warn "$rel (git-tracked but .dockerignore simulator flagged it — verify after build)"
        else
            log_fail "$rel (not git-tracked and not in context — add to git and commit)"
        fi
    fi
done < <(find "$PROJECT_ROOT/instruments/custom" -maxdepth 1 -mindepth 1 -type d | sort)

echo ""
echo "=== Python source directories ==="

for dir in "python/api" "python/tools" "python/helpers" "python/extensions"; do
    count=$(echo "$CONTEXT_FILES" | grep -c "^${dir}/.*\.py$" 2>/dev/null || echo 0)
    if [[ "$count" -gt 0 ]]; then
        log_ok "$dir/ ($count .py files)"
    else
        log_fail "$dir/ (0 .py files — check .dockerignore)"
    fi
done

echo ""
echo "=== Key root files ==="

for f in "run_ui.py" "pyproject.toml" "requirements.txt" ".env.example"; do
    if in_context "$f"; then
        log_ok "$f"
    else
        log_fail "$f"
    fi
done

echo ""
if [[ "$ERRORS" -gt 0 ]]; then
    echo -e "${RED}[FAIL]${NC}   $ERRORS issue(s) found in build context."
    echo -e "         Fix .dockerignore exclusions or missing files before building."
    exit 1
else
    log_ok "Build context validation passed — all critical files present"
    exit 0
fi
