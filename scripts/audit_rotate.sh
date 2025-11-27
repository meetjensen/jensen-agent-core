#!/usr/bin/env bash
set -euo pipefail
cd /volume1/JENSEN/agents/my-agent
set -a; [ -f ./.env ] && . ./.env; set +a

LOG="/volume1/JENSEN/agents/my-agent/logs/audit_rotate.log"
DATA="/volume1/JENSEN/agents/my-agent/data"
ARCH_META="$DATA/archives.jsonl"
KEEP="${AUDIT_ROTATE_KEEP:-5}"

echo "[$(date -Is)] rotate start" >> "$LOG"

STAMP=$(date +%Y%m%d-%H%M%S)
TMP="/tmp/jensen-audit-$STAMP"
mkdir -p "$TMP"

for d in data data/audit logs app/data; do
  [ -d "$d" ] || continue
  find "$d" -maxdepth 1 -type f \( -name '*.ndjson' -o -name '*.jsonl' -o -name '*audit*.ndjson' \) \
    -print -exec mv -f {} "$TMP"/ \; 2>/dev/null || true
done

COUNT=$(ls -1 "$TMP" 2>/dev/null | wc -l | tr -d ' ')
if [ "$COUNT" -eq 0 ]; then
  echo "[$(date -Is)] nothing to rotate" >> "$LOG"
  exit 0
fi

ARCHIVE="/volume1/JENSEN/agents/my-agent/releases/audit-${STAMP}.tar.gz"
tar -C "$TMP" -czf "$ARCHIVE" . && rm -rf "$TMP"
SIZE=$(stat -c%s "$ARCHIVE" 2>/dev/null || stat -f%z "$ARCHIVE")
SHA=$( (sha256sum "$ARCHIVE" 2>/dev/null || shasum -a 256 "$ARCHIVE") | awk '{print $1}' )

# Append metadata JSONL
mkdir -p "$DATA"
printf '{"ts":"%s","archive":"%s","count":%d,"size":%s,"sha256":"%s"}\n' "$(date -Is)" "$ARCHIVE" "$COUNT" "$SIZE" "$SHA" >> "$ARCH_META"

# Emit a Prometheus textfile metric for node_exporter (if available); otherwise no-op
METDIR="/var/lib/node_exporter/textfile_collector"
if [ -d "$METDIR" ]; then
  printf 'jensen_archives_created_total 1\n' > "$METDIR/jensen_archives.prom.$$" && mv "$METDIR/jensen_archives.prom.$$" "$METDIR/jensen_archives.prom"
fi

# Retention
ls -1t /volume1/JENSEN/agents/my-agent/releases/audit-*.tar.gz 2>/dev/null | tail -n +$((KEEP+1)) | xargs -r rm -f
echo "[$(date -Is)] archived -> $ARCHIVE (COUNT=$COUNT SIZE=$SIZE) ; retention KEEP=$KEEP done" >> "$LOG"
