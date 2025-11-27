#!/bin/sh
set -e
echo "Local:"
curl -fsS http://127.0.0.1:8000/health && echo

echo "External (via reverse proxy):"
curl -fsS https://ccity.synology.me/health -k && echo
