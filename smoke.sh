#!/bin/sh
set -e
HOST="${HOST:-https://agent.meetjensen.com}"
TOKEN="${TOKEN:-jensen4254}"
echo "# health"
curl -sS "$HOST/health"; echo
echo "# version"
curl -sS "$HOST/version"; echo
echo "# chat"
curl -sS -H "Content-Type: application/json" -H "X-Agent-Token: $TOKEN" \
  -d '{"message":"Reply only: PONG"}' "$HOST/chat"; echo
echo "# metrics"
curl -sS "$HOST/metrics"; echo
