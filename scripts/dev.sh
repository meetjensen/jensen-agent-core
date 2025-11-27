#!/bin/sh
set -eu
CF="/volume1/JENSEN/agents/my-agent/docker-compose.yml"
# Pre-clean: ignore errors if not present
docker compose -f "$CF" down --remove-orphans >/dev/null 2>&1 || true
docker rm -f jensen-agent >/dev/null 2>&1 || true
docker compose -f "$CF" up -d --build
echo "🚀 Jensen Agent running → https://ccity.synology.me"
