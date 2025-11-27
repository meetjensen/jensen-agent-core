#!/bin/sh
set -eu

BASE="/volume1/JENSEN/agents/my-agent"
TS="$(date +%F-%H%M%S)"
BACKUP="/volume1/JENSEN/releases/model-switch-backup-$TS.tar.gz"

echo "== Jensen Agent model switch =="
echo "Project: $BASE"
mkdir -p /volume1/JENSEN/releases

# 0) Backup everything (safe to undo)
echo ">> Creating backup: $BACKUP"
tar -czf "$BACKUP" -C "$BASE" \
  .env app *.md *.txt *.yml *.yaml *.py Makefile scripts templates \
  2>/dev/null || true
echo "Backup saved."

# 1) Preview: where do we reference gpt-4o ?
echo ">> Scanning for old model references (preview):"
grep -RIn --exclude-dir=.git --exclude-dir=__pycache__ --exclude-dir=venv \
  -e 'gpt-4o' -e 'chatgpt-4o-latest' "$BASE" || echo "(no matches)"

# 2) Replace in files (code + docs)
echo ">> Replacing model IDs in files..."
# We operate only on known text file types
find "$BASE" \( -name "*.py" -o -name "*.md" -o -name "*.txt" -o -name "*.yml" -o -name "*.yaml" -o -name "Makefile" -o -name ".env" \) \
  -type f -print0 | while IFS= read -r -d '' f; do
    # Create a per-file backup once (only if not already backed up globally)
    cp -n "$f" "$f.bak.$TS" 2>/dev/null || true

    # Do the replacements (longest → shortest to avoid partial overlaps)
    # BusyBox/BSD-compatible sed -i with backup suffix:
    sed -i.bak -e 's/chatgpt-4o-latest/gpt-5/g' \
               -e 's/gpt-4o-mini/gpt-5/g' \
               -e 's/gpt-4o-[0-9][0-9][0-9][0-9]-[0-9-]*/gpt-5/g' \
               -e 's/gpt-4o/gpt-5/g' "$f" || true
  done

# 3) Normalize .env MODEL_NAME (authoritative)
if [ -f "$BASE/.env" ]; then
  # If line exists, replace; else append
  if grep -q '^MODEL_NAME=' "$BASE/.env"; then
    sed -i.bak -e 's/^MODEL_NAME=.*/MODEL_NAME=gpt-5/' "$BASE/.env"
  else
    printf "\nMODEL_NAME=gpt-5\n" >> "$BASE/.env"
  fi
fi

# 4) Post-change summary
echo ">> Post-change scan:"
grep -RIn --exclude-dir=.git --exclude-dir=__pycache__ --exclude-dir=venv \
  -e 'gpt-4o' -e 'chatgpt-4o-latest' "$BASE" || echo "(no old model mentions remain)"

echo ">> Current MODEL_NAME line:"
grep -n '^MODEL_NAME=' "$BASE/.env" || echo "(no MODEL_NAME found)"

echo "Done. Backup = $BACKUP"
