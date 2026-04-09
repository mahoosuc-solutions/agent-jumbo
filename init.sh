#!/usr/bin/env bash
# agent-mahoo init — shell entry point for the interactive setup wizard.
# Usage: ./init.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/scripts/init.py" "$@"
