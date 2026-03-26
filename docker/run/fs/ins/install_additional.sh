#!/bin/bash
set -e

# install playwright - moved to install A0
# bash /ins/install_playwright.sh "$@"

# searxng - moved to base image
# bash /ins/install_searxng.sh "$@"

if [ "${INSTALL_ADDITIONAL_TOOLS:-1}" = "1" ]; then
    # Install diagram generation dependencies
    echo "Installing diagram generation tools..."

    # Install Mermaid CLI for diagram export
    npm install -g @mermaid-js/mermaid-cli

    echo "Diagram tools installation complete."
else
    echo "Skipping additional tool install because INSTALL_ADDITIONAL_TOOLS=${INSTALL_ADDITIONAL_TOOLS}"
fi
