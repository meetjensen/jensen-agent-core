#!/bin/sh
set -eu
CF="/volume1/JENSEN/agents/my-agent/docker-compose.yml"
docker compose -f "$CF" down --remove-orphans >/dev/null 2>&1 || true
docker rm -f jensen-agent >/dev/null 2>&1 || true
docker compose -f "$CF" up -d
