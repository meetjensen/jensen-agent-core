#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

ts=$(date +%Y%m%d-%H%M%S)
LIST="/tmp/backup_list.$ts"
DEST="_archive/backup_sweep_$ts"

# prune heavy/forbidden dirs early
find . \
  \( -path './data' -o -path './pgdata' -o -path './_archive' -o -path './_snapshots' -o -path './.git' \) -prune -o \
  -name '@eaDir' -prune -o \
  -type f \( -name '*.bak' -o -name '*.bak.*' -o -name '*.backup' -o -name '*.backup.*' -o \
            -name '*~'    -o -name '*.old'    -o -name '*.old.*'  -o \
            -name '*.tmp' -o -name '*.swp'    -o -name '*.sw?'    -o \
            -name '*.orig' -o -name '*.orig.*' -o \
            -name '*.copy' -o -name '*.copy.*' -o \
            -name '*.py.bak*' -o -name '*.yml.bak*' -o -name '*.env.bak*' -o -name '*.md.bak*' \
          \) -print0 > "$LIST"

count=$(tr -cd '\0' < "$LIST" | wc -c)
echo "[sweep] files found: $count"
[ "$count" -eq 0 ] && exit 0

mkdir -p "$DEST"
rsync -a --files-from="$LIST" --from0 ./ "$DEST"/
xargs -0 -I{} rm -v -- "{}" < "$LIST"

# pack result (skip @eaDir)
find "$DEST" -path '*/@eaDir' -prune -o -type f -print0 | tar --null -czf "${DEST}.tgz" -T -
sha256sum "${DEST}.tgz" > "${DEST}.tgz.sha256"
rm -rf "$DEST"
echo "[sweep] archive: ${DEST}.tgz"
