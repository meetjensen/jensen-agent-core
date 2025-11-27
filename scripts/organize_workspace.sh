#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

APPLY=${1:-}
ts=$(date +%Y%m%d-%H%M%S)
DEST="_archive/legacy_dirs_$ts"

# candidates in project root (not touching required dirs)
mapfile -t DIRS < <(find . -maxdepth 1 -type d \
  \( -name '_backup*' -o -name '_backups*' -o -name '_snapshots*' -o -name '_snapshots_final' \) \
  ! -name '.' ! -name './_archive' | sort)

echo "[tidy] candidates:"
printf '  %s\n' "${DIRS[@]:-<none>}"

if [ "$APPLY" != "--apply" ]; then
  echo "[tidy] preview only. Use: $0 --apply"
  exit 0
fi

[ "${#DIRS[@]}" -eq 0 ] && { echo "[tidy] nothing to move"; exit 0; }

mkdir -p "$DEST"
for d in "${DIRS[@]}"; do
  echo "[tidy] moving $d -> $DEST/$d"
  rsync -a "$d"/ "$DEST/$d"/ || true
  rm -rf "$d"
done

# optional: pack and remove expanded copy
find "$DEST" -path '*/@eaDir' -prune -o -type f -print0 | tar --null -czf "${DEST}.tgz" -T -
sha256sum "${DEST}.tgz" > "${DEST}.tgz.sha256"
rm -rf "$DEST"
echo "[tidy] archive: ${DEST}.tgz"
