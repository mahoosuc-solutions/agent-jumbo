#!/usr/bin/env bash
set -euo pipefail

# Agent Mahoo One-Line Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/mahoosuc-solutions/agent-mahoo/main/install.sh | bash

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
    echo "Agent Mahoo supports Linux and macOS only." >&2
    exit 1
fi

# Step 2 — Set install dir
if [ "$OS" = "Darwin" ]; then
    INSTALL_DIR="${HOME}/Library/Application Support/agent-mahoo"
else
    INSTALL_DIR="${HOME}/.local/share/agent-mahoo"
fi

# Step 3 — Fetch latest VERSION from GitHub API
REPO="mahoosuc-solutions/agent-mahoo"
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

VERSION=$(echo "${RELEASE_JSON}" | grep '"tag_name"' | head -1 | sed 's/.*"tag_name"[[:space:]]*:[[:space:]]*"v\{0,1\}\([^"]*\)".*/\1/')

if [ -z "$VERSION" ]; then
    echo "ERROR: Failed to determine latest version from GitHub API." >&2
    echo "API response: ${RELEASE_JSON:0:200}" >&2
    exit 1
fi

# Step 4 — Download and extract
ARCHIVE_NAME="agent-mahoo-${VERSION}.tar.gz"
DOWNLOAD_URL="https://github.com/${REPO}/releases/latest/download/${ARCHIVE_NAME}"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "${TMP_DIR}"' EXIT

echo "Downloading Agent Mahoo v${VERSION}..."
if command -v curl &>/dev/null; then
    curl -fsSL "${DOWNLOAD_URL}" -o "${TMP_DIR}/${ARCHIVE_NAME}"
elif command -v wget &>/dev/null; then
    wget -qO "${TMP_DIR}/${ARCHIVE_NAME}" "${DOWNLOAD_URL}"
else
    echo "ERROR: curl or wget required to download archive" >&2
    exit 1
fi

echo "Extracting to ${INSTALL_DIR}..."
if [ -d "${INSTALL_DIR}" ]; then
    echo "Removing existing installation..."
    rm -rf "${INSTALL_DIR}"
fi
mkdir -p "${INSTALL_DIR}"
tar -xzf "${TMP_DIR}/${ARCHIVE_NAME}" -C "${INSTALL_DIR}" --strip-components=1

# Step 5 — Check for uv, install if missing
if ! command -v uv &>/dev/null; then
    echo "Installing uv (Python package manager)..."
    # NOTE: This executes a remote script from the official Astral domain.
    # Review https://astral.sh/uv/install.sh before running in security-sensitive environments.
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="${HOME}/.local/bin:${PATH}"
    if ! command -v uv &>/dev/null; then
        echo "ERROR: uv installation failed. Install manually: https://docs.astral.sh/uv/" >&2
        exit 1
    fi
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
cat > "${INSTALL_DIR}/agent-mahoo" << 'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")"
exec uv run python run_ui.py "$@"
EOF
chmod +x "${INSTALL_DIR}/agent-mahoo"

# Step 8 — Create symlink to launcher
if [ "$OS" = "Darwin" ]; then
    LINK_DIR="/usr/local/bin"
    # Try to symlink to /usr/local/bin, fall back to ~/.local/bin if it fails
    if ! ln -sf "${INSTALL_DIR}/agent-mahoo" "${LINK_DIR}/agent-mahoo" 2>/dev/null; then
        echo "Note: /usr/local/bin not writable, using ~/.local/bin instead"
        LINK_DIR="${HOME}/.local/bin"
        mkdir -p "${LINK_DIR}"
        ln -sf "${INSTALL_DIR}/agent-mahoo" "${LINK_DIR}/agent-mahoo"
    fi
else
    LINK_DIR="${HOME}/.local/bin"
    mkdir -p "${LINK_DIR}"
    ln -sf "${INSTALL_DIR}/agent-mahoo" "${LINK_DIR}/agent-mahoo"
fi

# Step 9 — Print success message
echo ""
echo "✓ Agent Mahoo v${VERSION} installed to ${INSTALL_DIR}"
echo ""
echo "To start:"
echo "  agent-mahoo"
echo ""
echo "Or directly:"
echo "  cd \"${INSTALL_DIR}\" && uv run python run_ui.py"
echo ""

# Warn if LINK_DIR not in PATH
if ! echo "${PATH}" | tr ':' '\n' | grep -qx "${LINK_DIR}"; then
    echo ""
    echo "NOTE: Add ${LINK_DIR} to your PATH."
    # Detect shell rc file
    case "${SHELL}" in
        */zsh)  RC_FILE="${HOME}/.zshrc" ;;
        */fish) RC_FILE="${HOME}/.config/fish/config.fish" ;;
        *)      RC_FILE="${HOME}/.bashrc" ;;
    esac
    echo "  Add to ${RC_FILE}:"
    echo "    export PATH=\"${LINK_DIR}:\${PATH}\""
fi
