#!/bin/sh
set -eu
[ $# -eq 1 ] || { echo "Usage: restore.sh /path/to/jensen-agent-YYYY-MM-DD.tar.gz"; exit 1; }
tar -xzf "$1" -C /volume1/JENSEN/agents
echo "✅ restored to /volume1/JENSEN/agents/my-agent"
