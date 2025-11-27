#!/bin/sh
set -e

PROJECT_DIR="/volume1/JENSEN/agents/my-agent"
cd "$PROJECT_DIR"

# Wait for local health to be ready
wait_health() {
  i=0
  until curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; do
    i=$((i+1))
    if [ $i -ge 20 ]; then
      echo "Health still failing after $i tries."
      return 1
    fi
    sleep 2
  done
  return 0
}

# Keep previous working image for rollback
OLD_IMAGE_ID="$(docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}' | awk '$1=="jensen-agent:latest"{print $2}')"

echo "==> Building image from compose (project: jensen-agent)..."
docker compose -p jensen-agent -f docker-compose.yml build

if [ -n "$OLD_IMAGE_ID" ]; then
  echo "==> Tagging previous image as jensen-agent:prev ($OLD_IMAGE_ID)"
  docker tag "$OLD_IMAGE_ID" jensen-agent:prev || true
fi

echo "==> Starting/Updating project (project: jensen-agent)..."
docker compose -p jensen-agent -f docker-compose.yml up -d

echo "==> Waiting for local health..."
wait_health && echo "OK" || { echo "Health check failed"; exit 1; }

echo "✅ Deploy complete."
