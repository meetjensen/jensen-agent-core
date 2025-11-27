#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
ts=$(date +%Y%m%d-%H%M%S)
dst="/volume1/JENSEN/backups/jensen_${ts}.tgz"
find app Dockerfile docker-compose.yml requirements.txt .env \
  -path '*/@eaDir' -prune -o -type f -print0 | tar --null -czf "$dst" -T -
sha256sum "$dst" > "${dst}.sha256"
echo "[mkbackup] wrote $dst"
