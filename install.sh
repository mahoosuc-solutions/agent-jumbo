#!/usr/bin/env bash
set -euo pipefail

# Agent Jumbo One-Line Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/mahoosuc-solutions/agent-jumbo/main/install.sh | bash

# Step 1 — OS and arch detection
OS="$(uname -s)"   # Linux or Darwin
ARCH="$(uname -m)" # x86_64, arm64, aarch64

# Normalize arch
if [ "$ARCH" = "aarch64" ]; then
    ARCH="arm64"
fi

# Validate OS
if [ "$OS" != "Linux" ] && [ "$OS" != "Darwin" ]; then
    echo "ERROR: Unsupported operating system: ${OS}" >&2
    echo "Agent Jumbo supports Linux and macOS only." >&2
    exit 1
fi

# Step 2 — Set install dir
if [ "$OS" = "Darwin" ]; then
    INSTALL_DIR="${HOME}/Library/Application Support/agent-jumbo"
else
    INSTALL_DIR="${HOME}/.local/share/agent-jumbo"
fi

# Step 3 — Fetch latest VERSION from GitHub API
REPO="mahoosuc-solutions/agent-jumbo"
API_URL="https://api.github.com/repos/${REPO}/releases/latest"

echo "Fetching latest version from GitHub..."
if command -v curl &>/dev/null; then
    RELEASE_JSON=$(curl -fsSL "${API_URL}")
elif command -v wget &>/dev/null; then
    RELEASE_JSON=$(wget -qO- "${API_URL}")
else
    echo "ERROR: curl or wget required" >&2
    exit 1
fi

VERSION=$(echo "${RELEASE_JSON}" | python3 -c "import sys,json; print(json.load(sys.stdin)['tag_name'].lstrip('v'))")

if [ -z "$VERSION" ]; then
    echo "ERROR: Failed to determine latest version" >&2
    exit 1
fi

# Step 4 — Download and extract
ARCHIVE_NAME="agent-jumbo-${VERSION}.tar.gz"
DOWNLOAD_URL="https://github.com/${REPO}/releases/latest/download/${ARCHIVE_NAME}"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "${TMP_DIR}"' EXIT

echo "Downloading Agent Jumbo v${VERSION}..."
if command -v curl &>/dev/null; then
    curl -fsSL "${DOWNLOAD_URL}" -o "${TMP_DIR}/${ARCHIVE_NAME}"
else
    wget -qO "${TMP_DIR}/${ARCHIVE_NAME}" "${DOWNLOAD_URL}"
fi

echo "Extracting to ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}"
tar -xzf "${TMP_DIR}/${ARCHIVE_NAME}" -C "${INSTALL_DIR}" --strip-components=1

# Step 5 — Check for uv, install if missing
if ! command -v uv &>/dev/null; then
    echo "Installing uv (Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add uv to PATH for rest of this script
    export PATH="${HOME}/.cargo/bin:${HOME}/.local/bin:${PATH}"
fi

# Step 6 — Install Python dependencies
echo "Installing Python dependencies..."
cd "${INSTALL_DIR}"
if uv sync --no-dev 2>/dev/null; then
    :  # Success
else
    echo "Falling back to full sync..."
    uv sync
fi

# Step 7 — Create launcher script
echo "Creating launcher script..."
cat > "${INSTALL_DIR}/agent-jumbo" << 'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")"
exec uv run python run_ui.py "$@"
EOF
chmod +x "${INSTALL_DIR}/agent-jumbo"

# Step 8 — Create symlink to launcher
if [ "$OS" = "Darwin" ]; then
    LINK_DIR="/usr/local/bin"
    # Try to symlink to /usr/local/bin, fall back to ~/.local/bin if it fails
    if ! ln -sf "${INSTALL_DIR}/agent-jumbo" "${LINK_DIR}/agent-jumbo" 2>/dev/null; then
        echo "Note: /usr/local/bin not writable, using ~/.local/bin instead"
        LINK_DIR="${HOME}/.local/bin"
        mkdir -p "${LINK_DIR}"
        ln -sf "${INSTALL_DIR}/agent-jumbo" "${LINK_DIR}/agent-jumbo"
    fi
else
    LINK_DIR="${HOME}/.local/bin"
    mkdir -p "${LINK_DIR}"
    ln -sf "${INSTALL_DIR}/agent-jumbo" "${LINK_DIR}/agent-jumbo"
fi

# Step 9 — Print success message
echo ""
echo "✓ Agent Jumbo v${VERSION} installed to ${INSTALL_DIR}"
echo ""
echo "To start:"
echo "  agent-jumbo"
echo ""
echo "Or directly:"
echo "  cd \"${INSTALL_DIR}\" && uv run python run_ui.py"
echo ""

# Warn if LINK_DIR not in PATH
if ! echo "${PATH}" | tr ':' '\n' | grep -qx "${LINK_DIR}"; then
    echo "NOTE: Add ${LINK_DIR} to your PATH:"
    if [ "$OS" = "Darwin" ]; then
        echo "  echo 'export PATH=\"${LINK_DIR}:\${PATH}\"' >> ~/.zshrc"
        echo "  source ~/.zshrc"
    else
        echo "  echo 'export PATH=\"${LINK_DIR}:\${PATH}\"' >> ~/.bashrc"
        echo "  source ~/.bashrc"
    fi
    echo ""
fi
