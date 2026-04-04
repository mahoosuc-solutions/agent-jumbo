#!/usr/bin/env bash
# ============================================
# Agent Jumbo Release Packaging Script
# ============================================
# Creates distributable .tar.gz and .zip archives
# for GitHub Releases. Users extract and run
# `uv sync && uv run python run_ui.py`.

set -euo pipefail

# Ensure we're running from repo root
if [[ ! -f "pyproject.toml" ]] || [[ ! -f "run_ui.py" ]]; then
    echo "[package-release] ERROR: Must run from repository root" >&2
    exit 1
fi

# Extract VERSION from pyproject.toml
# Try tomllib (Python 3.11+), fall back to tomli
VERSION=$(python3 -c "
try:
    import tomllib
    with open('pyproject.toml', 'rb') as f:
        data = tomllib.load(f)
        print(data['project']['version'])
except (ImportError, ModuleNotFoundError):
    import tomli
    with open('pyproject.toml', 'rb') as f:
        data = tomli.load(f)
        print(data['project']['version'])
" 2>/dev/null)

if [[ -z "${VERSION}" ]]; then
    echo "[package-release] ERROR: Could not read version from pyproject.toml" >&2
    exit 1
fi

echo "[package-release] Packaging Agent Jumbo v${VERSION}..."

# Create dist directory
DIST_DIR="dist/agent-jumbo-${VERSION}"
mkdir -p "${DIST_DIR}"

# Copy root Python files
echo "[package-release] Copying root files..."
for file in run_ui.py initialize.py preload.py prepare.py agent.py models.py; do
    if [[ -f "${file}" ]]; then
        cp "${file}" "${DIST_DIR}/"
    fi
done

# Copy directories
echo "[package-release] Copying directories..."
for dir in python webui instruments skills prompts conf docker; do
    if [[ -d "${dir}" ]]; then
        cp -r "${dir}" "${DIST_DIR}/"
    fi
done

# Copy knowledge directory (preserve structure)
echo "[package-release] Copying knowledge directory..."
if [[ -d "knowledge/default" ]]; then
    mkdir -p "${DIST_DIR}/knowledge"
    cp -r "knowledge/default" "${DIST_DIR}/knowledge/"
fi

# Copy Docker files
echo "[package-release] Copying Docker configuration..."
for file in DockerfileLocal docker-compose.yml; do
    if [[ -f "${file}" ]]; then
        cp "${file}" "${DIST_DIR}/"
    fi
done

# Copy dependency and config files
echo "[package-release] Copying dependency files..."
for file in pyproject.toml requirements.txt .env.example; do
    if [[ -f "${file}" ]]; then
        cp "${file}" "${DIST_DIR}/"
    fi
done

# Copy documentation and legal files
echo "[package-release] Copying documentation..."
for file in README.md LICENSE NOTICE; do
    if [[ -f "${file}" ]]; then
        cp "${file}" "${DIST_DIR}/"
    fi
done

# Copy install script if it exists
if [[ -f "install.sh" ]]; then
    echo "[package-release] Copying install.sh..."
    cp install.sh "${DIST_DIR}/"
fi

# Remove user data (database files in instruments/custom/*/data/)
echo "[package-release] Removing user data files..."
find "${DIST_DIR}/instruments/custom" -path "*/data/*.db" -delete 2>/dev/null || true

# Clean up Python cache and system files
echo "[package-release] Cleaning cache and temporary files..."
find "${DIST_DIR}" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "${DIST_DIR}" -name "*.pyc" -delete 2>/dev/null || true
find "${DIST_DIR}" -name "*.pyo" -delete 2>/dev/null || true
find "${DIST_DIR}" -name ".DS_Store" -delete 2>/dev/null || true

# Create archives
echo "[package-release] Creating archives..."
cd dist

# Create tar.gz
tar -czf "agent-jumbo-${VERSION}.tar.gz" "agent-jumbo-${VERSION}/"
TARGZ_SIZE=$(du -h "agent-jumbo-${VERSION}.tar.gz" | cut -f1)

# Create zip
zip -rq "agent-jumbo-${VERSION}.zip" "agent-jumbo-${VERSION}/"
ZIP_SIZE=$(du -h "agent-jumbo-${VERSION}.zip" | cut -f1)

cd ..

# Print summary
echo ""
echo "============================================"
echo "[package-release] Agent Jumbo v${VERSION} packaged:"
echo "  dist/agent-jumbo-${VERSION}.tar.gz  (${TARGZ_SIZE})"
echo "  dist/agent-jumbo-${VERSION}.zip     (${ZIP_SIZE})"
echo "============================================"
echo ""
echo "To verify contents:"
echo "  tar -tzf dist/agent-jumbo-${VERSION}.tar.gz | less"
echo "  unzip -l dist/agent-jumbo-${VERSION}.zip | less"
echo ""
