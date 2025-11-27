#!/bin/bash
set -euo pipefail
DRY=0
[[ "${1:-}" == "--dry-run" ]] && DRY=1

ROOT="/volume1/JENSEN/agents/my-agent"
ARCH="${ROOT}/_archive"
TS="$(date +%Y%m%d-%H%M%S)"
DST_ROOT="${ARCH}/consolidated_root_${TS}"
DST_APP="${ARCH}/consolidated_app_${TS}"
DST_BAKS="${ARCH}/file_baks_${TS}"

log(){ echo "[$(date +%H:%M:%S)] $*"; }

move_it () {
  # move source -> dest (mkdir -p); honor DRY
  local src="$1"; local dest="$2"
  mkdir -p "$dest"
  if [[ $DRY -eq 1 ]]; then
    log "DRY: mv -v \"$src\" \"$dest/\""
  else
    mv -v "$src" "$dest/" 2>/dev/null || true
  fi
}

log "Consolidating stray backup directories and .bak files into ${ARCH}"

# 1) ROOT-level backup-ish directories (but keep _archive, scripts, app, data, pgdata)
for d in "${ROOT}"/_*backup* "${ROOT}"/backup* "${ROOT}"/backups*; do
  [[ -e "$d" ]] || continue
  b="$(basename "$d")"
  case "$b" in
    _archive|scripts|app|data|pgdata) continue ;;
  esac
  move_it "$d" "$DST_ROOT"
done

# 2) APP-level backup-ish directories
for d in "${ROOT}/app"/_*backup* "${ROOT}/app"/backup* "${ROOT}/app"/backups*; do
  [[ -e "$d" ]] || continue
  move_it "$d" "$DST_APP"
done

# 3) Loose .bak/.old/.save files in app and app/static (e.g., main.py.bak.2025…)
find "${ROOT}/app" -maxdepth 1 -type f \( -iname "*.bak*" -o -iname "*.old*" -o -iname "*.save*" \) -print0 \
  | while IFS= read -r -d '' f; do move_it "$f" "$DST_BAKS"; done

find "${ROOT}/app/static" -maxdepth 1 -type f \( -iname "*.bak*" -o -iname "*.old*" -o -iname "*.save*" \) -print0 \
  | while IFS= read -r -d '' f; do move_it "$f" "$DST_BAKS"; done

# 4) Kill Synology @eaDir and empty folders inside my-agent root
find "${ROOT}" -type d -name '@eaDir' -prune -print0 | \
  while IFS= read -r -d '' d; do
    if [[ $DRY -eq 1 ]]; then log "DRY: rm -rv \"$d\""; else rm -rv "$d"; fi
  done

# Remove empty dirs left behind (non-recursive prune)
# (We try twice to catch parents that become empty after children removed)
for i in 1 2; do
  while IFS= read -r d; do
    if [[ $DRY -eq 1 ]]; then log "DRY: rmdir -v \"$d\""; else rmdir -v "$d" 2>/dev/null || true; fi
  done < <(find "${ROOT}" -type d -empty)
done

log "Consolidation complete."
log "NOTE: Next step is to prune _archive to keep only newest items. Use: ${ROOT}/scripts/cleanup_backups.sh"
