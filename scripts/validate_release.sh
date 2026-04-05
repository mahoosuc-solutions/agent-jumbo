#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="${REPORT_DIR:-$ROOT_DIR/artifacts/validation}"
TS="$(date +%Y%m%d-%H%M%S)"
REPORT_FILE="$REPORT_DIR/release-validation-$TS.log"

mkdir -p "$REPORT_DIR"

exec > >(tee "$REPORT_FILE") 2>&1

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
    if command -v python3.11 >/dev/null 2>&1; then
        PYTHON_BIN="python3.11"
    elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
        PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
    else
        PYTHON_BIN="python3"
    fi
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

pass() {
    echo -e "${GREEN}✓${NC} $1"
    PASS=$((PASS + 1))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    FAIL=$((FAIL + 1))
}

warn() {
    echo -e "${YELLOW}!${NC} $1"
}

check_cmd() {
    local name="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        pass "$name"
    else
        fail "$name"
    fi
}

check_file() {
    local label="$1"
    local path="$2"
    if [[ -f "$ROOT_DIR/$path" ]]; then
        pass "$label"
    else
        fail "$label"
    fi
}

check_dir_has_files() {
    local label="$1"
    local path="$2"
    if find "$ROOT_DIR/$path" -maxdepth 1 -type f | grep -q .; then
        pass "$label"
    else
        fail "$label"
    fi
}

check_dir_has_pattern() {
    local label="$1"
    local path="$2"
    local pattern="$3"
    if find "$ROOT_DIR/$path" -maxdepth 1 -type f -name "$pattern" | grep -q .; then
        pass "$label"
    else
        fail "$label"
    fi
}

check_text() {
    local label="$1"
    local pattern="$2"
    local path="$3"
    if rg -q "$pattern" "$ROOT_DIR/$path"; then
        pass "$label"
    else
        fail "$label"
    fi
}

run_optional_tool_check() {
    local name="$1"
    shift
    local tool="$1"
    shift

    if ! command -v "$tool" >/dev/null 2>&1; then
        fail "$name (missing command: $tool)"
        return
    fi

    if "$@" >/dev/null 2>&1; then
        pass "$name"
    else
        fail "$name"
    fi
}

check_python_release_version() {
    "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'
}

check_core_python_compile() {
    "$PYTHON_BIN" -m py_compile \
        python/helpers/tool.py \
        python/api/message.py \
        python/api/message_async.py \
        python/helpers/skill_registry.py
}

echo "Agent Jumbo Release Validation"
echo "=============================="
echo "Report: $REPORT_FILE"
echo ""

cd "$ROOT_DIR"

echo "Repository Checks:"
check_cmd "Git repository available" git rev-parse --is-inside-work-tree
check_cmd "Launch branch checked out" bash -lc 'branch="$(git rev-parse --abbrev-ref HEAD)"; [[ "$branch" == "main" || "$branch" == release* ]]'
check_cmd "Working tree clean" bash -lc '[[ -z "$(git status --porcelain)" ]]'
check_cmd "At least one tag exists" bash -lc 'git tag | grep -q .'

echo ""
echo "Core File Checks:"
check_file "LICENSE exists" "LICENSE"
check_file "README exists" "README.md"
check_file "CONTRIBUTING exists" "CONTRIBUTING.md"
check_file "CHANGELOG exists" "CHANGELOG.md"
check_file "SECURITY exists" "SECURITY.md"
check_file "INSTALL guide exists" "INSTALL.md"
check_file "Package metadata exists" "pyproject.toml"
check_file "Web package exists" "web/package.json"
check_file "Vercel config exists" "web/vercel.json"
check_file "GA definition exists" "docs/PRODUCTION_GA_DEFINITION_OF_DONE.md"
check_file "GA launch inventory exists" "docs/GA_LAUNCH_INVENTORY.md"
check_file "GA evidence package exists" "docs/GA_EVIDENCE_PACKAGE.md"
check_file "Self-serve onboarding exists" "docs/SELF_SERVE_GA_ONBOARDING.md"
check_file "GA launch runbook exists" "docs/GA_LAUNCH_RUNBOOK.md"
check_file "Customer support doc exists" "docs/CUSTOMER_SUPPORT.md"

echo ""
echo "Workflow and Script Checks:"
check_dir_has_files "GitHub workflows exist" ".github/workflows"
check_file "Validation 360 script exists" "scripts/validate_360.sh"
check_file "Release validation script exists" "scripts/validate_release.sh"
check_file "Deployment validation script exists" "scripts/validate_deployment.sh"
check_file "Post-deploy runtime validation script exists" "scripts/validate_post_deploy_runtime.py"
check_dir_has_pattern "Manual smoke artifact exists" "artifacts/validation" "manual-smoke-*.md"
check_dir_has_pattern "Compliance links artifact exists" "artifacts/validation" "compliance-links-*.md"

echo ""
echo "Metadata and Documentation Consistency:"
check_text "pyproject has package name" '^name = "agent-jumbo-devops"$' "pyproject.toml"
check_text "pyproject has version" '^version = ".+"$' "pyproject.toml"
check_text "pyproject has SPDX license" '^license = "Apache-2.0"$' "pyproject.toml"
check_text "README references deployment" 'Deployment Guide' "README.md"
check_text "Release checklist points to GA definition" 'Production GA Definition of Done' "docs/RELEASE_CHECKLIST.md"
check_text "Production deploy points to GA definition" 'Production GA Definition of Done' "docs/PRODUCTION_DEPLOY.md"
check_text "Docs index lists GA definition" 'Production GA Definition of Done' "docs/README.md"
check_text "Docs index lists customer support" 'Customer Support' "docs/README.md"
check_text "Support doc links issues" 'github.com/agent-jumbo-deploy/agent-jumbo/issues' "docs/CUSTOMER_SUPPORT.md"
check_text "Support doc links discussions" 'github.com/agent-jumbo-deploy/agent-jumbo/discussions' "docs/CUSTOMER_SUPPORT.md"
check_text "Support doc references billing support" 'Billing And Payment Support' "docs/CUSTOMER_SUPPORT.md"
check_text "Web docs page features support doc" "slug: 'CUSTOMER_SUPPORT'" "web/app/(public)/documentation/page.tsx"
check_text "Pricing page links support doc" '/documentation/CUSTOMER_SUPPORT' "web/app/(public)/pricing/page.tsx"
check_text "Pricing page links privacy doc" '/documentation/PRIVACY_POLICY' "web/app/(public)/pricing/page.tsx"
check_text "Pricing page links terms doc" '/documentation/TERMS_OF_USE' "web/app/(public)/pricing/page.tsx"
check_text "GA inventory references refreshed manual smoke" 'manual-smoke-20260405.md' "docs/GA_LAUNCH_INVENTORY.md"
check_text "GA inventory records compliance verification" 'compliance-links-20260405.md' "docs/GA_LAUNCH_INVENTORY.md"

echo ""
echo "Python Validation:"
check_cmd "Python 3.11+ available for release tooling" check_python_release_version
check_text "pyproject declares Python 3.11+" '^requires-python = ">=3.11"$' "pyproject.toml"
check_cmd "Core files compile" check_core_python_compile

echo ""
echo "Web Validation:"
run_optional_tool_check "web/package.json has build script" jq jq -e '.scripts.build' web/package.json
run_optional_tool_check "web/package.json has type-check script" jq jq -e '.scripts["type-check"]' web/package.json

echo ""
echo "Summary:"
echo -e "  ${GREEN}Passed: $PASS${NC}"
echo -e "  ${RED}Failed: $FAIL${NC}"
echo ""

if [[ "$FAIL" -eq 0 ]]; then
    echo -e "${GREEN}Release validation passed.${NC}"
    echo "Report saved to: $REPORT_FILE"
    exit 0
fi

warn "Release validation failed. Fix the items above before treating the repo as release-ready."
echo "Report saved to: $REPORT_FILE"
exit 1
