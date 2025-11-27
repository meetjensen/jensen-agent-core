#!/usr/bin/env bash
set -euo pipefail
BASE="https://agent.meetjensen.com"
TOKEN="jensen4254"

curl -skfS "$BASE/health" | grep -q '"ok": true'
curl -skfS "$BASE/version" | grep -E '"version"\s*:\s*".+?"'

curl -skfS -H 'Content-Type: application/json' \
  -H "X-Agent-Token: $TOKEN" \
  -d '{"message":"smoke test"}' \
  "$BASE/chat" | grep -q '"reply"'

echo "SMOKE OK"
