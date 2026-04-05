#!/bin/bash
set -e

# activate venv
. "/ins/setup_venv.sh" "$@"

# install playwright if not installed (should be from requirements.txt)
uv pip install playwright

# Use stable path outside /aj so browsers survive the source COPY layer.
# PLAYWRIGHT_BROWSERS_PATH may already be set by Dockerfile ENV; default here as fallback.
export PLAYWRIGHT_BROWSERS_PATH=${PLAYWRIGHT_BROWSERS_PATH:-/opt/playwright}

# install chromium with dependencies
apt-get install -y fonts-unifont libnss3 libnspr4 libatk1.0-0 libatspi2.0-0 libxcomposite1 libxdamage1 libatk-bridge2.0-0 libcups2
playwright install chromium --only-shell
