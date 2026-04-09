#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f docker/base/Dockerfile ]]; then
  echo "docker/base/Dockerfile not found"
  exit 1
fi

docker build -f docker/base/Dockerfile -t agent-mahoo-base:local docker/base
echo "Built reusable base image: agent-mahoo-base:local"
