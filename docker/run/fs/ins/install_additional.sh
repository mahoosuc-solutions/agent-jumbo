#!/bin/bash
set -e

# install playwright - moved to install A0
# bash /ins/install_playwright.sh "$@"

# searxng - moved to base image
# bash /ins/install_searxng.sh "$@"

if [ "${INSTALL_ADDITIONAL_TOOLS:-1}" = "1" ]; then
    # Install diagram generation dependencies
    if [ "${INSTALL_MERMAID_CLI:-1}" = "1" ]; then
        echo "Installing diagram generation tools..."
        npm install -g @mermaid-js/mermaid-cli
        echo "Diagram tools installation complete."
    else
        echo "Skipping Mermaid CLI install because INSTALL_MERMAID_CLI=${INSTALL_MERMAID_CLI}"
    fi

    # Install Claude Code CLI (authenticates via host credential store)
    echo "Installing Claude Code CLI..."
    npm install -g @anthropic-ai/claude-code
    echo "Claude Code CLI installation complete."

    # Install Codex CLI (authenticates via host credential store)
    echo "Installing Codex CLI..."
    npm install -g @openai/codex
    echo "Codex CLI installation complete."
else
    echo "Skipping additional tool install because INSTALL_ADDITIONAL_TOOLS=${INSTALL_ADDITIONAL_TOOLS}"
fi
