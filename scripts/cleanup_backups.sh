#!/bin/bash
set -euo pipefail
DRY=0
[[ "${1:-}" == "--dry-run" ]] && DRY=1

ROOT="/volume1/JENSEN/agents/my-agent"
ARCH="$ROOT/_archive"

log(){ echo "[$(date +%H:%M:%S)] $*"; }

keep_newest_files() {
  # usage: keep_newest_files "glob pattern"
  shopt -s nullglob
  local matches=( $1 )
  shopt -u nullglob
  (( ${#matches[@]} <= 1 )) && return 0
  # sort by mtime desc
  mapfile -t sorted < <(ls -1t "${matches[@]}" 2>/dev/null || true)
  for ((i=1;i<${#sorted[@]};i++)); do
    if (( DRY==1 )); then log "DRY: rm -v \"${sorted[$i]}\""; else rm -v "${sorted[$i]}"; fi
  done
}

keep_newest_dirs() {
  # usage: keep_newest_dirs "glob pattern"
  compgen -G "$1" > /dev/null || return 0
  mapfile -t sorted < <(ls -1dt $1 2>/dev/null || true)
  for ((i=1;i<${#sorted[@]};i++)); do
    if (( DRY==1 )); then log "DRY: rm -rv \"${sorted[$i]}\""; else rm -rv "${sorted[$i]}"; fi
  done
}

if [[ ! -d "$ARCH" ]]; then
  log "Archive not found: $ARCH (nothing to clean)"
  exit 0
fi

log "Pruning inside: $ARCH  (keeping newest per group)"
# TGZ groups
keep_newest_files "$ARCH"/pre_*".tgz"
keep_newest_files "$ARCH"/rollback_guard_*.tgz
keep_newest_files "$ARCH"/backups_only_*.tgz
keep_newest_files "$ARCH"/pre_cleanup_*.tgz
keep_newest_files "$ARCH"/pre_css_fix_*.tgz

# CSS backups
keep_newest_files "$ARCH"/final.css.*.css
keep_newest_files "$ARCH"/theme.css.*.css

# Directory groups
keep_newest_dirs "$ARCH"/css_locked_*
keep_newest_dirs "$ARCH"/guard_*

# Kill Synology @eaDir and empty dirs
find "$ARCH" -type d -name '@eaDir' -prune -print0 | xargs -0 -I{} bash -c '[[ "$DRY" == "1" ]] && echo "DRY: rm -rv \"{}\"" || rm -rv "{}"'
# Remove empty directories
while read -r d; do
  if (( DRY==1 )); then log "DRY: rmdir -v \"$d\""; else rmdir -v "$d" 2>/dev/null || true; fi
done < <(find "$ARCH" -type d -empty)

log "Done. Current contents & size:"
du -sh "$ARCH" 2>/dev/null || true
ls -lah "$ARCH" | sed -n '1,200p'
