#!/bin/bash
set -e

# Exit immediately if a command exits with a non-zero status.
# set -e

# branch from parameter
if [ -z "$1" ]; then
    echo "Error: Branch parameter is empty. Please provide a valid branch name."
    exit 1
fi
BRANCH="$1"

if [ "$BRANCH" = "local" ]; then
    # For local branch, use the files
    echo "Using local dev files in /git/agent-jumbo"
    # List all files recursively in the target directory
    # echo "All files in /git/agent-jumbo (recursive):"
    # find "/git/agent-jumbo" -type f | sort
else
    # For other branches, clone from GitHub
    echo "Cloning repository from branch $BRANCH..."
    git clone -b "$BRANCH" "https://github.com/mahoosuc-solutions/agent-jumbo" "/git/agent-jumbo" || {
        echo "CRITICAL ERROR: Failed to clone repository. Branch: $BRANCH"
        exit 1
    }
fi

. "/ins/setup_venv.sh" "$@"

# moved to base image
# # Ensure the virtual environment and pip setup
# pip install --upgrade pip ipython requests
# # Install some packages in specific variants
# pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining A0 python packages
uv pip install -r /git/agent-jumbo/requirements.txt
# override for packages that have unnecessarily strict dependencies
uv pip install -r /git/agent-jumbo/requirements2.txt

# install playwright unless explicitly disabled for slimmer runtime builds
if [ "${INSTALL_PLAYWRIGHT:-1}" = "1" ]; then
    bash /ins/install_playwright.sh "$@"
else
    echo "Skipping Playwright install because INSTALL_PLAYWRIGHT=${INSTALL_PLAYWRIGHT}"
fi

# Preload models unless explicitly disabled for slimmer runtime builds
if [ "${RUN_PRELOAD:-1}" = "1" ]; then
    python /git/agent-jumbo/preload.py --dockerized=true
else
    echo "Skipping preload because RUN_PRELOAD=${RUN_PRELOAD}"
fi
