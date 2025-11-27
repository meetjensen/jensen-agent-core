#!/usr/bin/env bash
set -euo pipefail
cd /volume1/JENSEN/releases
# keep last 8 jensen-agent_*.tgz by mtime; leave legacy_* alone
ls -1t jensen-agent_*.tgz 2>/dev/null | awk 'NR>8{print}' | while read -r f; do
  echo "[rotate] removing $f and its sha256"
  rm -f "$f" "$f.sha256"
done
# rebuild index
TS=$(date +%Y%m%d-%H%M%S)
{
  echo "# Jensen Agent Releases (generated $TS)"; echo
  for f in *.tgz; do
    [ -f "$f" ] || continue
    sz=$(du -h "$f" | awk '{print $1}')
    sh=$(cut -d' ' -f1 "$f.sha256" 2>/dev/null || true)
    printf -- "• %s  |  %s  |  sha256:%s\n" "$f" "$sz" "${sh:-n/a}"
  done | sort
} > RELEASES_INDEX.md
