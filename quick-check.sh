#!/bin/sh
set -e
echo "# Local"
curl -sS http://127.0.0.1:8000/health; echo
curl -sS http://127.0.0.1:8000/version; echo
curl -sS -w '\nHTTP:%{http_code}\n' http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' -H 'X-Agent-Token: jensen4254' \
  -d '{"message":"Reply with the single word: OK"}'
echo "# Public"
curl -sS https://agent.meetjensen.com/health; echo
curl -sS https://agent.meetjensen.com/version; echo
curl -sS -w '\nHTTP:%{http_code}\n' https://agent.meetjensen.com/chat \
  -H 'Content-Type: application/json' -H 'X-Agent-Token: jensen4254' \
  -d '{"message":"Reply with the single word: OK"}'
