#!/usr/bin/env bash
set -euo pipefail
cd /volume1/JENSEN/agents/my-agent

# Allowlisted files that must NOT be treated as clutter
ALLOW_RE='^scripts/(restore\.sh|preflight\.sh|release_rotate\.sh|sweep_backups\.sh|organize_workspace\.sh|mkbackup\.sh)$'

# Build list of suspicious files (common backup/junk patterns)
bad_raw=$(find . \
  \( -path './data' -o -path './pgdata' -o -path './_archive' -o -path './.git' \) -prune -o \
  -name '@eaDir' -prune -o \
  -type f \( \
      -name '*.bak' -o -name '*.bak.*' -o -name '*.backup' -o -name '*.backup.*' -o \
      -name '*~'    -o -name '*.old'    -o -name '*.old.*'  -o \
      -name '*.tmp' -o -name '*.swp'    -o -name '*.sw?'    -o \
      -name '*.orig' -o -name '*.orig.*' -o \
      -name '*.copy' -o -name '*.copy.*' -o \
      -name '*.py.bak*' -o -name '*.yml.bak*' -o -name '*.env.bak*' -o -name '*.md.bak*' -o \
      -name '*rollback*' -o -name '*.restore*' -o -name '*_restore_*' -o -name '*restore*.bak*' \
    \) -print | sed 's#^\./##')

# Filter out allowlisted paths
bad=""
IFS=$'\n'
for f in $bad_raw; do
  echo "$f" | grep -Eq "$ALLOW_RE" && continue
  bad+="$f"$'\n'
done

if [ -n "${bad:-}" ]; then
  echo "[workspace-guard] Refusing to proceed due to backup clutter:"
  printf "%s" "$bad"
  exit 1
fi
echo "[workspace-guard] OK"
